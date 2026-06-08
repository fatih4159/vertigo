import re
from typing import List, Optional
from app.models.job_posting import WorkModel


TECH_PATTERNS: dict = {
    "React": [r"\breact(\.js)?\b", r"\breactjs\b"],
    "Angular": [r"\bangular\b"],
    "Vue": [r"\bvue(\.js)?\b", r"\bvuejs\b"],
    "JavaScript": [r"\bjavascript\b", r"\bjs\b(?!on)"],
    "TypeScript": [r"\btypescript\b", r"\bts\b"],
    "Node.js": [r"\bnode\.?js\b", r"\bnodejs\b"],
    "Python": [r"\bpython\b"],
    "Django": [r"\bdjango\b"],
    "Flask": [r"\bflask\b"],
    "FastAPI": [r"\bfastapi\b"],
    "Java": [r"\bjava\b(?!script)"],
    "Spring": [r"\bspring(\ ?boot)?\b"],
    "Kotlin": [r"\bkotlin\b"],
    "PHP": [r"\bphp\b"],
    "Laravel": [r"\blaravel\b"],
    "Symfony": [r"\bsymfony\b"],
    "C#": [r"\bc#\b", r"\bcsharp\b"],
    ".NET": [r"\b\.net\b", r"\bdotnet\b", r"\basp\.net\b"],
    "Go": [r"\bgolang\b", r"\bgo\b(?= ?(lang|developer|engineer))"],
    "Rust": [r"\brust\b(?!y)"],
    "Docker": [r"\bdocker\b"],
    "Kubernetes": [r"\bkubernetes\b", r"\bk8s\b"],
    "AWS": [r"\baws\b", r"\bamazon web services\b"],
    "Azure": [r"\bazure\b", r"\bmicrosoft azure\b"],
    "GCP": [r"\bgcp\b", r"\bgoogle cloud\b"],
    "Terraform": [r"\bterraform\b"],
    "PostgreSQL": [r"\bpostgresql\b", r"\bpostgres\b"],
    "MySQL": [r"\bmysql\b"],
    "MongoDB": [r"\bmongodb\b", r"\bmongo\b"],
    "Redis": [r"\bredis\b"],
    "GraphQL": [r"\bgraphql\b"],
    "REST": [r"\brest(?:ful)?\s+api\b", r"\brest api\b"],
    "Microservices": [r"\bmicroservices?\b"],
    "Swift": [r"\bswift\b"],
    "Flutter": [r"\bflutter\b"],
    "React Native": [r"\breact\s+native\b"],
    "Next.js": [r"\bnext\.?js\b"],
    "Nuxt": [r"\bnuxt\.?js?\b"],
}

REMOTE_PATTERNS = [
    r"\bremote\b",
    r"\bwork from home\b",
    r"\bwfh\b",
    r"\bfull remote\b",
    r"\b100%\s*remote\b",
    r"\bremote-first\b",
    r"\bhome ?office\b",
    r"\barbeiten von zuhause\b",
    r"\bremote arbeit\b",
    r"\bvollst.ndig remote\b",
]

HYBRID_PATTERNS = [
    r"\bhybrid\b",
    r"\bpartially remote\b",
    r"\bremote.{0,20}office\b",
    r"\boffice.{0,20}remote\b",
    r"\bflexible.{0,20}remote\b",
    r"\bhybrides arbeiten\b",
    r"\bhybrid work\b",
    r"\bteilweise remote\b",
]

SENIOR_PATTERNS = [
    r"\bsenior\b",
    r"\blead\b",
    r"\bprincipal\b",
    r"\bstaff\b",
    r"\barchitect\b",
    r"\bcto\b",
    r"\bhead of\b",
    r"\bvp\b",
]

JUNIOR_PATTERNS = [
    r"\bjunior\b",
    r"\bintern\b",
    r"\bpraktikant\b",
    r"\bwerkstudent\b",
    r"\btrainee\b",
    r"\bgraduate\b",
    r"\bentry.level\b",
]


class AnalysisService:
    def extract_tech_stack(self, text: str) -> List[str]:
        if not text:
            return []
        text_lower = text.lower()
        found = []
        for tech, patterns in TECH_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    if tech not in found:
                        found.append(tech)
                    break
        return found

    def classify_work_model(self, text: str) -> WorkModel:
        if not text:
            return WorkModel.UNKNOWN
        text_lower = text.lower()
        for pattern in HYBRID_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return WorkModel.HYBRID
        for pattern in REMOTE_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return WorkModel.REMOTE
        return WorkModel.ON_SITE

    def calculate_score(self, title: str, description: str, tech_stack: List[str]) -> int:
        score = 0
        text = f"{title} {description or ''}".lower()

        # Tech stack contributes up to 30 points
        tech_score = min(len(tech_stack) * 3, 30)
        score += tech_score

        # Seniority signals
        for pattern in SENIOR_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                score += 15
                break

        # Deduct for junior roles
        for pattern in JUNIOR_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                score -= 10
                break

        # Multiple open positions hint at larger hiring
        hiring_signals = [
            r"\b\d+\s+(?:open|new)\s+positions?\b",
            r"\bgrowing team\b",
            r"\bscaling\b",
            r"\bexpanding\b",
            r"\brapid growth\b",
            r"\bwachsendes team\b",
        ]
        for pattern in hiring_signals:
            if re.search(pattern, text, re.IGNORECASE):
                score += 5
                break

        # Cloud & modern tech bonus
        modern_tech = {"Docker", "Kubernetes", "AWS", "Azure", "GCP", "Terraform", "Microservices"}
        overlap = modern_tech.intersection(set(tech_stack))
        score += len(overlap) * 3

        return max(0, min(100, score))

    def extract_location(self, text: str, fallback: Optional[str] = None) -> Optional[str]:
        if not text:
            return fallback
        # German and European city patterns
        city_pattern = r"\b(Berlin|Hamburg|Munich|München|Frankfurt|Cologne|Köln|Stuttgart|Düsseldorf|Leipzig|Dresden|Nuremberg|Nürnberg|Bremen|Hannover|Dortmund|Essen|Bochum|Wuppertal|Bielefeld|Bonn|Mannheim|Karlsruhe|Wiesbaden|Augsburg|Aachen|Vienna|Wien|Zurich|Zürich|Basel|Bern|Amsterdam|Rotterdam|Utrecht|London|Paris|Madrid|Barcelona|Milan|Milano|Remote|Deutschlandweit)\b"
        match = re.search(city_pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)
        return fallback

    def analyze_job(self, title: str, description: str, location_hint: Optional[str] = None) -> dict:
        combined_text = f"{title} {description or ''}"
        tech_stack = self.extract_tech_stack(combined_text)
        work_model = self.classify_work_model(combined_text)
        score = self.calculate_score(title, description, tech_stack)
        location = self.extract_location(combined_text, fallback=location_hint)
        return {
            "tech_stack": tech_stack,
            "work_model": work_model,
            "score": score,
            "location": location,
        }
