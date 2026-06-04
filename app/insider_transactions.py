"""SEC Form 4 insider-transaction tracking for Atlas Lite."""

from datetime import date, timedelta
import json
import logging
import os
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from app.growth import GrowthEngine


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INSIDER_CACHE_DIR = PROJECT_ROOT / "data_cache" / "insider_transactions"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_ARCHIVE_INDEX_URL = "https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession}/index.json"
SEC_ARCHIVE_DOCUMENT_URL = "https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession}/{document}"
INSIDER_LOOKBACK_DAYS = 14
INSIDER_SUBMISSIONS_CACHE_HOURS = 12
INSIDER_FILING_CACHE_DAYS = 30
INSIDER_TIMEOUT_SECONDS = 10
SEC_REQUEST_DELAY_SECONDS = 0.12


TRANSACTION_LABELS = {
    "P": "Purchase",
    "S": "Sale",
    "A": "Acquisition/award",
    "D": "Disposition",
    "F": "Tax withholding",
    "G": "Gift",
    "M": "Option exercise",
}


class InsiderTransactionTracker:
    """Fetch and cache recent SEC Form 4 transactions for Atlas securities."""

    def __init__(self, cache_dir=DEFAULT_INSIDER_CACHE_DIR):
        self.cache_dir = Path(cache_dir)
        self.logger = logging.getLogger(__name__)
        self.growth_engine = GrowthEngine()
        self.user_agent = os.getenv(
            "ATLAS_SEC_USER_AGENT",
            "Atlas Capital Research atlas.capital.reports@gmail.com",
        )

    def fetch_transactions(
        self,
        market_data,
        lookback_days=INSIDER_LOOKBACK_DAYS,
        max_events=12,
        today=None,
    ):
        """Fetch recent Form 4 non-derivative transactions for current Atlas companies."""
        today = today or date.today()
        cutoff = today - timedelta(days=lookback_days)
        transactions = []

        for ticker, data in sorted(market_data.items()):
            if data.get("sector") == "Benchmark ETF":
                continue

            cik = self.growth_engine._get_cik(ticker)
            if not cik:
                continue

            submissions = self._fetch_submissions(cik)
            for filing in self._recent_form4_filings(submissions, cutoff):
                filing_transactions = self._fetch_filing_transactions(
                    ticker=ticker,
                    company_name=data.get("company_name") or ticker,
                    cik=cik,
                    filing=filing,
                )
                transactions.extend(filing_transactions)

        return sorted(
            transactions,
            key=lambda item: (item.get("transaction_date", ""), item.get("ticker", "")),
            reverse=True,
        )[:max_events]

    def _fetch_submissions(self, cik):
        return self._fetch_json_cached(
            SEC_SUBMISSIONS_URL.format(cik=cik),
            f"submissions_{cik}.json",
            INSIDER_SUBMISSIONS_CACHE_HOURS,
        )

    def _recent_form4_filings(self, submissions, cutoff):
        if not submissions:
            return []

        recent = submissions.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        filings = []

        for index, form in enumerate(forms):
            if form not in {"4", "4/A"}:
                continue

            filing_date = self._date_from_string(self._value_at(recent, "filingDate", index))
            report_date = self._date_from_string(self._value_at(recent, "reportDate", index))
            comparison_date = report_date or filing_date
            if comparison_date is None or comparison_date < cutoff:
                continue

            filings.append(
                {
                    "accession_number": self._value_at(recent, "accessionNumber", index),
                    "filing_date": filing_date.isoformat() if filing_date else "N/A",
                    "report_date": report_date.isoformat() if report_date else "N/A",
                    "primary_document": self._value_at(recent, "primaryDocument", index),
                }
            )

        return filings

    def _fetch_filing_transactions(self, ticker, company_name, cik, filing):
        accession_number = filing.get("accession_number")
        document_name = self._raw_document_name(filing.get("primary_document"))
        if not accession_number or not document_name:
            document_name = self._find_raw_xml_document(cik, accession_number)
        if not accession_number or not document_name:
            return []

        xml_text = self._fetch_filing_xml(cik, accession_number, document_name)
        if not xml_text:
            return []

        return self._parse_form4_xml(
            ticker=ticker,
            company_name=company_name,
            cik=cik,
            filing=filing,
            xml_text=xml_text,
        )

    def _parse_form4_xml(self, ticker, company_name, cik, filing, xml_text):
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            self.logger.warning("Unable to parse Form 4 XML for %s: %s", ticker, exc)
            return []

        owner_name = self._text(root, "reportingOwner/reportingOwnerId/rptOwnerName") or "Unknown owner"
        owner_title = self._text(root, "reportingOwner/reportingOwnerRelationship/officerTitle")
        accession_number = filing.get("accession_number")
        filing_url = self._filing_url(cik, accession_number)
        transactions = []

        for transaction in root.findall("nonDerivativeTable/nonDerivativeTransaction"):
            transaction_code = self._text(transaction, "transactionCoding/transactionCode") or "N/A"
            shares = self._float_text(transaction, "transactionAmounts/transactionShares/value")
            price = self._float_text(transaction, "transactionAmounts/transactionPricePerShare/value")
            acquired_disposed = self._text(
                transaction,
                "transactionAmounts/transactionAcquiredDisposedCode/value",
            )
            transaction_date = self._text(transaction, "transactionDate/value") or filing.get("report_date")
            total_value = shares * price if shares is not None and price is not None else None

            transactions.append(
                {
                    "ticker": ticker,
                    "company_name": company_name,
                    "owner_name": owner_name,
                    "owner_title": owner_title or "N/A",
                    "transaction_date": transaction_date or "N/A",
                    "filing_date": filing.get("filing_date", "N/A"),
                    "transaction_code": transaction_code,
                    "transaction_label": TRANSACTION_LABELS.get(transaction_code, transaction_code),
                    "acquired_disposed": acquired_disposed or "N/A",
                    "shares": shares,
                    "price": price,
                    "total_value": total_value,
                    "filing_url": filing_url,
                    "source": "sec_form4",
                }
            )

        return transactions

    def _find_raw_xml_document(self, cik, accession_number):
        if not accession_number:
            return None
        accession = accession_number.replace("-", "")
        index_url = SEC_ARCHIVE_INDEX_URL.format(cik_int=int(cik), accession=accession)
        payload = self._fetch_json_cached(
            index_url,
            f"filing_index_{accession}.json",
            INSIDER_FILING_CACHE_DAYS * 24,
        )
        for item in payload.get("directory", {}).get("item", []) if payload else []:
            name = item.get("name", "")
            if name.endswith(".xml") and not name.endswith("-index.xml"):
                return name
        return None

    def _fetch_filing_xml(self, cik, accession_number, document_name):
        accession = accession_number.replace("-", "")
        url = SEC_ARCHIVE_DOCUMENT_URL.format(
            cik_int=int(cik),
            accession=accession,
            document=document_name,
        )
        return self._fetch_text_cached(
            url,
            f"filing_{accession}_{Path(document_name).name}",
            INSIDER_FILING_CACHE_DAYS,
        )

    def _fetch_json_cached(self, url, cache_filename, max_age_hours):
        cache_path = self.cache_dir / cache_filename
        cached_payload = self._read_cached_json(cache_path)

        if cached_payload is not None and self._cache_is_fresh(cache_path, max_age_hours):
            return cached_payload

        payload = self._fetch_json_uncached(url)
        if payload is not None:
            self._write_cached_json(cache_path, payload)
            return payload

        if cached_payload is not None:
            self.logger.warning("Using stale insider JSON cache after fetch failure: %s", cache_path)
            return cached_payload
        return None

    def _fetch_text_cached(self, url, cache_filename, max_age_days):
        cache_path = self.cache_dir / cache_filename
        cached_text = self._read_cached_text(cache_path)

        if cached_text is not None and self._cache_is_fresh(cache_path, max_age_days * 24):
            return cached_text

        text = self._fetch_text_uncached(url)
        if text is not None:
            self._write_cached_text(cache_path, text)
            return text

        if cached_text is not None:
            self.logger.warning("Using stale insider filing cache after fetch failure: %s", cache_path)
            return cached_text
        return None

    def _fetch_json_uncached(self, url):
        text = self._fetch_text_uncached(url, accept="application/json")
        if text is None:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            self.logger.warning("Unable to parse SEC JSON from %s: %s", url, exc)
            return None

    def _fetch_text_uncached(self, url, accept="application/xml,text/plain,application/json"):
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": accept,
            },
        )
        try:
            time.sleep(SEC_REQUEST_DELAY_SECONDS)
            with urllib.request.urlopen(request, timeout=INSIDER_TIMEOUT_SECONDS) as response:
                return response.read().decode("utf-8", errors="replace")
        except Exception as exc:
            self.logger.warning("Unable to retrieve SEC insider data from %s: %s", url, exc)
            return None

    def _read_cached_json(self, cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except Exception as exc:
            self.logger.warning("Unable to read insider JSON cache %s: %s", cache_path, exc)
            return None

    def _write_cached_json(self, cache_path, payload):
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(payload, f)
        except Exception as exc:
            self.logger.warning("Unable to write insider JSON cache %s: %s", cache_path, exc)

    def _read_cached_text(self, cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return None
        except Exception as exc:
            self.logger.warning("Unable to read insider filing cache %s: %s", cache_path, exc)
            return None

    def _write_cached_text(self, cache_path, text):
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(text)
        except Exception as exc:
            self.logger.warning("Unable to write insider filing cache %s: %s", cache_path, exc)

    def _cache_is_fresh(self, cache_path, max_age_hours):
        try:
            age_seconds = time.time() - cache_path.stat().st_mtime
        except FileNotFoundError:
            return False
        return age_seconds <= max_age_hours * 60 * 60

    def _raw_document_name(self, primary_document):
        if not primary_document:
            return None
        name = str(primary_document).split("/")[-1]
        return name if name.endswith(".xml") else None

    def _filing_url(self, cik, accession_number):
        if not accession_number:
            return ""
        accession = accession_number.replace("-", "")
        return SEC_ARCHIVE_INDEX_URL.format(cik_int=int(cik), accession=accession).replace(
            "/index.json",
            f"/{accession_number}-index.html",
        )

    def _value_at(self, payload, key, index):
        values = payload.get(key, [])
        return values[index] if index < len(values) else None

    def _date_from_string(self, value):
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None

    def _text(self, root, path):
        element = root.find(path)
        if element is None or element.text is None:
            return None
        return element.text.strip()

    def _float_text(self, root, path):
        value = self._text(root, path)
        if value is None:
            return None
        try:
            return float(value.replace(",", ""))
        except ValueError:
            return None
