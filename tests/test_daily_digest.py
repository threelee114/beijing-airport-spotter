import json
import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import daily_digest as digest


DAY = datetime(2026, 11, 28, tzinfo=digest.CST)


def row(scheduled=13, estimated=None, reg="B-2006", airline="Air China (Retro)"):
    times = {"scheduled": {"arrival": int(DAY.replace(hour=scheduled).timestamp())}}
    if estimated is not None:
        times["estimated"] = {"arrival": int(DAY.replace(hour=estimated).timestamp())}
    return {"flight": {"time": times, "aircraft": {"registration": reg},
                       "identification": {"number": {"default": "CA123"}},
                       "airline": {"name": airline, "code": {"iata": "CA"}}}}


def page(rows, pages=1):
    arrivals = {"data": rows, "page": {"total": pages}}
    return {"result": {"response": {"airport": {"pluginData": {"schedule": {"arrivals": arrivals}}}}}}


class DigestTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.state = Path(temp.name)
        self.enterContext(patch.dict(os.environ, DIGEST_SENT_DIR=str(self.state / "sent")))

    def run_digest(self, *args, response=None, smtp_error=None, airports="PEK"):
        argv = ["digest", "--date", "2026-11-28", "--state-dir", str(self.state), "--airports", airports, *args]
        with patch.object(sys, "argv", argv), patch.object(digest, "fetch_page", side_effect=response), \
             patch.object(digest, "send_smtp", side_effect=smtp_error) as smtp, patch("time.sleep"):
            return digest.main(), smtp

    def test_failure_keeps_snapshot_and_fails_job(self):
        snapshot = self.state / "arrivals.json"
        snapshot.write_text("previous scan")
        for response in (lambda *a, **k: {}, lambda *a, **k: page(None)):
            code, smtp = self.run_digest(response=response)
            self.assertNotEqual(code, 0)
            smtp.assert_not_called()
            self.assertEqual(snapshot.read_text(), "previous scan")

    def test_empty_airport_is_successful(self):
        code, smtp = self.run_digest(response=lambda *a, **k: page([]))
        self.assertEqual(code, 0)
        self.assertIn("PEK 0 班", smtp.call_args.args[1])

    def test_partial_pages_and_failed_airport_are_visible(self):
        def fetch(airport, anchor, number, **kwargs):
            if airport == "PEK" and number == 1:
                return page([row()], 2)
            raise RuntimeError("FR24 HTTP 403")
        code, smtp = self.run_digest(airports="PEK,PKX", response=fetch)
        self.assertEqual(code, 0)
        body = smtp.call_args.args[1]
        for fragment in ("CA123", "部分", "PKX 抓取失败"):
            self.assertIn(fragment, body)
        self.assertNotIn("PKX 0 班", body)

    def test_retry_after_smtp_failure_then_skip_after_success(self):
        def fetch(*a, **k):
            return page([row()])
        with self.assertRaisesRegex(RuntimeError, "SMTP"):
            self.run_digest(response=fetch, smtp_error=RuntimeError("SMTP"))
        code, mail = self.run_digest("--diff-only", response=fetch)
        self.assertEqual(code, 0)
        mail.assert_called_once()
        _, mail = self.run_digest("--diff-only", response=fetch)
        mail.assert_not_called()

    def test_dry_run_does_not_suppress_morning_delivery(self):
        self.run_digest("--dry-run", response=lambda *a, **k: page([row()]))
        _, mail = self.run_digest("--diff-only", response=lambda *a, **k: page([row()]))
        mail.assert_called_once()

    def test_eta_moves_flight_to_dark_section_and_keeps_schedule(self):
        code, smtp = self.run_digest(response=lambda *a, **k: page([row(13, 21)]))
        self.assertEqual(code, 0)
        dark = smtp.call_args.args[1].split("夜间被过滤参考区")[1]
        self.assertIn("21:00", dark)
        self.assertIn("原定 13:00", dark)

    def test_known_registration_wins_over_regional_suffix(self):
        self.run_digest(response=lambda *a, **k: page([row(airline="Air China (Regional)")]))
        ap = json.loads((self.state / "arrivals.json").read_text(encoding="utf-8"))["airports"]["PEK"]
        self.assertEqual(len(ap["special_liveries"]), 1)
        self.assertIn(digest.KNOWN_SPECIAL_LIVERIES["B-2006"], ap["special_liveries"][0]["reasons"][0])

    def test_overnight_delay_keeps_service_date_and_uses_next_days_light(self):
        flight = row(23, 13)
        flight["flight"]["time"]["estimated"]["arrival"] += 86400
        _, smtp = self.run_digest(response=lambda *a, **k: page([flight]))
        main, dark = smtp.call_args.args[1].split("夜间被过滤参考区")
        self.assertIn("11-29 13:00", main)
        self.assertIn("原定 23:00", main)
        self.assertNotIn("CA123", dark)

    def test_legacy_snapshot_is_not_delivery_evidence(self):
        self.run_digest(response=lambda *a, **k: page([row()]))
        (self.state / "sent" / "2026-11-28.json").unlink()
        _, smtp = self.run_digest("--diff-only", response=lambda *a, **k: page([row()]))
        smtp.assert_called_once()

    def test_min_hour_filter_does_not_mark_omitted_arrivals_as_sent(self):
        morning, noon = row(9), row(13)
        morning["flight"]["identification"]["number"]["default"] = "CA456"
        def fetch(*a, **k):
            return page([morning, noon])
        _, first = self.run_digest("--diff-only", "--min-hour", "10", response=fetch)
        self.assertNotIn("CA456", first.call_args.args[1])
        _, second = self.run_digest("--diff-only", response=fetch)
        self.assertIn("CA456", second.call_args.args[1])
        self.assertNotIn("CA123", second.call_args.args[1])

    def commercial(self, model="A320", reg="B-TEST", minutes=0):
        flight = row(airline="Air China", reg=reg)
        flight["flight"]["aircraft"]["model"] = {"code": model}
        flight["flight"]["time"]["estimated"] = {"arrival": int(DAY.replace(hour=13).timestamp()) + minutes * 60}
        return flight

    def deliver(self, *flights, diff=False, smtp_error=None):
        _, mail = self.run_digest(*(["--diff-only"] if diff else []),
                                  response=lambda *a, **k: page(list(flights)), smtp_error=smtp_error)
        return mail.call_args.args[1] if mail.called else ""

    def test_livery_change_pending_and_confirmed_replacement(self):
        self.deliver(self.commercial())
        self.assertIn("换上彩绘", self.deliver(self.commercial(reg="B-2006"), diff=True))
        uncertain = self.deliver(self.commercial(reg=""), diff=True)
        self.assertIn("注册号待确认", uncertain)
        self.assertNotIn("原定彩绘已换走", uncertain)
        self.assertEqual(self.deliver(self.commercial(reg=""), diff=True), "")
        self.assertIn("原定彩绘已换走", self.deliver(self.commercial(reg="B-NEW"), diff=True))

    def test_model_changes_and_eta_retries(self):
        self.deliver(self.commercial())
        for model, name in (("342", "A340-200"), ("B748", "747-8"), ("388", "A380-800")):
            body = self.deliver(self.commercial(model), diff=True)
            self.assertIn("重点机型", body)
            self.assertIn(name, body)
        with self.assertRaisesRegex(RuntimeError, "SMTP"):
            self.deliver(self.commercial("A388", minutes=45), diff=True, smtp_error=RuntimeError("SMTP"))
        body = self.deliver(self.commercial("A388", minutes=45), diff=True)
        self.assertIn("推迟 45 分钟", body)
        self.assertIn("13:45", body)
        self.assertEqual(self.deliver(self.commercial("388", minutes=45), diff=True), "")
        self.assertIn("重点机型已换走", self.deliver(self.commercial(), diff=True))

    def test_missing_flight_is_not_a_swap(self):
        self.deliver(self.commercial("B744", reg="B-2006"))
        self.assertEqual(self.deliver(diff=True), "")
        self.assertIn("推迟 45 分钟", self.deliver(self.commercial("B744", reg="B-2006", minutes=45), diff=True))

    def test_header_reports_when_each_airport_was_checked(self):
        def fetch(airport, *a, **k):
            if airport == "PKX":
                raise RuntimeError("403")
            return page([])
        _, smtp = self.run_digest(airports="PEK,PKX", response=fetch)
        header = smtp.call_args.args[1].split("<h3")[0]
        self.assertRegex(header, r"PEK 0 班.*?抓取完整.*?\d{2}:\d{2}")
        self.assertRegex(header, r"PKX 抓取失败.*?\d{2}:\d{2}")
        self.assertIn("北京时间", header)

    def test_airports_do_not_share_a_change_baseline(self):
        self.deliver(self.commercial("B744", reg="B-2006"))
        self.run_digest(airports="PKX", response=lambda *a, **k: page([self.commercial()]))
        _, mail = self.run_digest("--diff-only", airports="PKX", response=lambda *a, **k: page([self.commercial()]))
        mail.assert_not_called()
        self.assertIn("重点机型已换走", self.deliver(self.commercial(), diff=True))

    def test_live_commercial_arrivals_share_equipment_aliases(self):
        import live_alert
        flight = self.commercial("74H")
        flight["flight"]["status"] = {"live": True}
        def fetch(url, **kwargs):
            return page([flight] if "code=pek" in url and "page=1" in url else [])
        with patch.object(live_alert, "http_get_json", side_effect=fetch):
            alerts = live_alert.scan_fr24_live_arrivals(DAY.replace(hour=12), set())
            self.assertEqual(len(alerts), 1)
            self.assertIn("747-8", " ".join(alerts[0]["reasons"]))
            known = {"FLTR:CA123:B-TEST"}
            self.assertEqual(live_alert.scan_fr24_live_arrivals(DAY.replace(hour=12), known), [])

    def test_first_comparison_and_ordinary_eta_do_not_create_a_change(self):
        self.assertNotIn("民航彩绘与重点机型变更", self.deliver(self.commercial()))
        self.assertEqual(self.deliver(self.commercial(minutes=45), diff=True), "")

    def test_model_can_be_identified_by_its_description(self):
        f = self.commercial("")
        f["flight"]["aircraft"]["model"]["text"] = "Boeing 747-400F"
        self.assertIn("重点机型 747-400F", self.deliver(f))

    def test_eta_change_from_daylight_to_night_is_reported(self):
        self.deliver(self.commercial("A342"))
        self.assertIn("推迟 480 分钟", self.deliver(self.commercial("A342", minutes=480), diff=True))

    def test_heavy_aircraft_swap_within_same_model(self):
        self.deliver(self.commercial("74N", reg="B-OLD"))
        body = self.deliver(self.commercial("74N", reg="B-NEW"), diff=True)
        self.assertIn("重点机型换机：747-8F，B-OLD → B-NEW", body)
        self.assertEqual(self.deliver(self.commercial("74N", reg="B-NEW"), diff=True), "")
