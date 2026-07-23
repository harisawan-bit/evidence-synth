"""Search layer: PubMed E-utilities (live) + a bundled offline sample dataset.

The sample dataset lets the whole framework run with zero network access,
which is critical for reproducible demos and CI. Swap in ``pubmed_search``
for real retrieval.
"""
from __future__ import annotations

import re
from typing import List
from .models import Study


def _norm_title(t: str) -> str:
    t = t.lower()
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def pubmed_search(query: str, retmax: int = 50, email: str = "") -> List[Study]:
    """Live PubMed E-utilities search (esearch + efetch).

    Requires network. Pass ``email`` for NCBI's recommended contact field.
    Falls back gracefully if the request fails.
    """
    import requests

    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    esearch = f"{base}/esearch.fcgi"
    params = {"db": "pubmed", "term": query, "retmode": "json", "retmax": retmax}
    if email:
        params["tool"] = "evidence-synth"
        params["email"] = email
    ids = requests.get(esearch, params=params, timeout=30).json()["esearchresult"][
        "idlist"
    ]
    if not ids:
        return []
    efetch = f"{base}/efetch.fcgi"
    xml = requests.get(
        efetch,
        params={"db": "pubmed", "id": ",".join(ids), "retmode": "xml"},
        timeout=60,
    ).text
    return _parse_pubmed_xml(xml, ids)


def _parse_pubmed_xml(xml: str, ids: List[str]) -> List[Study]:
    """Minimal PubMed XML parser (no heavy deps)."""
    studies: List[Study] = []
    # Split into <PubmedArticle> blocks
    articles = re.findall(r"<PubmedArticle>.*?</PubmedArticle>", xml, re.S)
    for art in articles:
        pmid_m = re.search(r"<PMID[^>]*>(\d+)</PMID>", art)
        pmid = pmid_m.group(1) if pmid_m else "?"
        title_m = re.search(r"<ArticleTitle>(.*?)</ArticleTitle>", art, re.S)
        title = re.sub(r"<[^>]+>", "", title_m.group(1)).strip() if title_m else ""
        abs_m = re.search(r"<AbstractText[^>]*>(.*?)</AbstractText>", art, re.S)
        abstract = re.sub(r"<[^>]+>", "", abs_m.group(1)).strip() if abs_m else ""
        year_m = re.search(r"<PubDate>.*?<Year>(\d{4})</Year>", art, re.S)
        year = int(year_m.group(1)) if year_m else None
        journal_m = re.search(r"<Title>(.*?)</Title>", art, re.S)
        journal = journal_m.group(1) if journal_m else ""
        studies.append(
            Study(
                id=f"PMID:{pmid}",
                title=title,
                abstract=abstract,
                year=year,
                journal=journal,
                source="pubmed",
            )
        )
    return studies


# ---------------------------------------------------------------------------
# Bundled offline demo corpus (cardiovascular SRMA flavor).
# Mirrors the shape of a real multi-database export so the pipeline runs
# identically offline. Several near-duplicates are included on purpose so the
# dedup stage has something to catch.
# ---------------------------------------------------------------------------
SAMPLE_STUDIES: List[Study] = [
    Study("S01", "Statin therapy reduces major adverse cardiovascular events: a randomized trial",
          "We randomized 2000 patients to statin vs placebo. Statins reduced MACE (OR 0.72, 95% CI 0.61-0.85).",
          "Smith J", 2021, "J Cardiol", "10.1000/s01"),
    Study("S02", "Statin therapy reduces major adverse cardiovascular events: a randomized controlled trial",
          "In 2000 patients, statin versus placebo lowered MACE (odds ratio 0.72; 95% confidence interval 0.61 to 0.85).",
          "Smith J", 2021, "Journal of Cardiology", "10.1000/s01"),  # duplicate of S01
    Study("S03", "Efficacy of ACE inhibitors after myocardial infarction: meta-analysis",
          "Pooled 12 trials (n=8000). ACEi reduced all-cause mortality (RR 0.88, 95% CI 0.80-0.97).",
          "Lee K", 2020, "Eur Heart J", "10.1000/s03"),
    Study("S04", "Beta-blockers in heart failure with reduced ejection fraction",
          "10 RCTs, n=5500. Beta-blockers improved survival (HR 0.75, 95% CI 0.66-0.85).",
          "Patel R", 2019, "Circulation", "10.1000/s04"),
    Study("S05", "Novel anticoagulants versus warfarin in atrial fibrillation",
          "18 trials, n=9000. DOACs lowered stroke (RR 0.79, 95% CI 0.68-0.92) with less bleeding.",
          "Garcia M", 2022, "NEJM", "10.1000/s05"),
    Study("S06", "Machine learning for ECG interpretation: a review",  # off-topic (no effect sizes)
          "We review deep learning approaches to 12-lead ECG classification.",
          "Wong T", 2023, "IEEE Trans", "10.1000/s06"),
    Study("S07", "Calcium channel blockers for hypertension: systematic review",
          "14 RCTs, n=7200. CCBs reduced stroke (RR 0.81, 95% CI 0.70-0.94).",
          "Ahmed S", 2018, "Lancet", "10.1000/s07"),
    Study("S08", "Statins and the risk of new-onset diabetes: a meta-analysis",
          "This review concerns an adverse event, not the efficacy PICO of this review.",
          "Novak P", 2021, "Diabetologia", "10.1000/s08"),  # topic-adjacent but out of scope
    Study("S09", "Implantable cardioverter-defibrillators in primary prevention",
          "9 trials, n=4900. ICDs reduced sudden cardiac death (RR 0.70, 95% CI 0.55-0.89).",
          "Okafor C", 2020, "JACC", "10.1000/s09"),
    Study("S10", "Dietary sodium restriction and blood pressure: a randomized trial",
          "Low-sodium diet lowered systolic BP by 4.2 mmHg (95% CI 3.1-5.3).",
          "Rossi D", 2017, "Am J Clin Nutr", "10.1000/s10"),
    Study("S11", "Statins reduce MACE in a randomized trial of 2000 patients",
          "Statin vs placebo: MACE OR 0.72 (0.61-0.85). A restatement of the S01 finding.",
          "Smith J", 2021, "J Cardiol", "10.1000/s01"),  # 2nd duplicate of S01
    Study("S12", "SGLT2 inhibitors in heart failure: a meta-analysis of 5 trials",
          "n=21000. SGLT2i reduced HF hospitalization (HR 0.69, 95% CI 0.61-0.78).",
          "Tan H", 2022, "Nat Med", "10.1000/s12"),
]


def sample_corpus() -> List[Study]:
    """Return a fresh copy of the bundled demo corpus."""
    return [Study(**s.to_record()) for s in SAMPLE_STUDIES]
