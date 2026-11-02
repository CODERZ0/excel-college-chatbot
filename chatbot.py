"""
Excel Engineering College — Extreme Offline Knowledge Assistant
- Fully offline retrieval; no API, internet, or paid model.
- Reads the complete knowledge_base.txt at startup.
- Uses BM25-style ranking, section-aware retrieval, course/entity detection,
  concise answer formatting, and per-session conversation context.
- Public API: chatbot.get_response(message, session_id="...")
"""

from pathlib import Path
from collections import Counter
import math
import re

BASE = Path(__file__).resolve().parent
KB_PATH = BASE / "knowledge_base.txt"

STOP = set("""
a an the is are was were be been being do does did can could would should will
i we you they he she it my our your me us them what which who whom when why how
where please tell show give want need about for of to in on at with from and or
this that there their college excel engineering eec details information
""".split())

ALIASES = {
    "admission": {"admissions", "apply", "application", "joining", "join", "enroll", "enrolment", "eligibility", "tnea", "counselling", "counseling"},
    "course": {"courses", "programme", "programmes", "program", "programs", "degree", "degrees", "study", "studies"},
    "department": {"departments", "branch", "branches", "school", "schools"},
    "fee": {"fees", "tuition", "payment", "cost", "scholarship", "scholarships"},
    "placement": {"placements", "recruitment", "job", "jobs", "career", "training", "internship", "companies"},
    "contact": {"phone", "telephone", "mobile", "email", "mail", "reach", "call", "enquiry", "enquiries"},
    "location": {"located", "address", "where", "directions", "map", "highway"},
    "hostel": {"accommodation", "room", "rooms", "mess"},
    "facility": {"facilities", "laboratory", "laboratories", "lab", "library", "sports", "transport", "bus", "internet"},
    "history": {"established", "founded", "founder", "year", "trust"},
    "exam": {"examination", "exams", "result", "results", "syllabus", "curriculum", "calendar", "coe"},
    "research": {"innovation", "entrepreneurship", "incubation", "patent", "patents", "publication"},
    "vision": {"mission", "objective", "objectives", "aim", "aims"},
}

INTENT_TERMS = {
    "courses": {"course", "courses", "programme", "programmes", "degree", "study"},
    "admission": {"admission", "admissions", "apply", "application", "join", "joining", "eligibility", "tnea"},
    "fees": {"fee", "fees", "tuition", "scholarship", "scholarships"},
    "placements": {"placement", "placements", "recruitment", "career", "training"},
    "contact": {"contact", "phone", "email", "telephone", "call"},
    "facilities": {"facility", "facilities", "hostel", "library", "transport", "sports", "laboratory"},
    "departments": {"department", "departments", "branch", "branches"},
    "location": {"location", "address", "located", "where", "directions"},
}

COURSE_NAMES = [
    "B.Tech Artificial Intelligence and Data Science",
    "B.E. Computer Science and Engineering",
    "B.E. CSE (Artificial Intelligence and Machine Learning)",
    "B.Tech Information Technology",
    "B.Tech Computer Science and Business Systems",
    "M.E. Computer Science and Engineering",
    "M.Tech Computer Science and Engineering (Integrated 5 Years)",
    "B.E. Electronics and Communication Engineering",
    "B.E. Electrical and Electronics Engineering",
    "B.E. Biomedical Engineering",
    "M.E. Applied Electronics",
    "M.E. Biomedical Engineering",
    "M.E. Embedded Systems Technologies",
    "M.E. Power Electronics and Drives",
    "B.E. Aeronautical Engineering",
    "B.E. Civil Engineering",
    "B.E. Mechanical Engineering",
    "M.E. Thermal Engineering",
    "Agricultural Engineering", "Food Technology", "Petrochemical Technology",
    "B.E. Safety and Fire Engineering", "MBA", "Integrated MBA (5 years)",
    "MCA", "B.Arch", "M.Arch"
]

def words(text):
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 1 and w not in STOP]

def norm(text):
    return " ".join(words(text))

def expand(tokens):
    out = list(tokens)
    for t in tokens:
        for root, related in ALIASES.items():
            if t == root or t in related:
                out.extend([root, *related])
    return list(dict.fromkeys(out))

def split_sections(text):
    lines = text.replace("\r\n", "\n").split("\n")
    sections, title, buffer = [], "College information", []
    for raw in lines:
        line = raw.strip()
        if re.match(r"^\d{1,2}\.\s+[A-Za-z]", line):
            if buffer:
                sections.append((title, "\n".join(buffer).strip()))
            title, buffer = line, [line]
        elif line:
            # Skip isolated scraped domains/source markers, but retain substantive content.
            if re.fullmatch(r"(source:|copy|open|[a-z0-9.-]+\.(com|edu|in|org))", line, re.I):
                continue
            buffer.append(line)
    if buffer:
        sections.append((title, "\n".join(buffer).strip()))
    return sections

class OfflineCollegeBot:
    def __init__(self, path=KB_PATH):
        self.path = Path(path)
        self.sessions = {}
        self.reload_knowledge()

    def reload_knowledge(self):
        if not self.path.exists():
            raise FileNotFoundError(f"Missing {self.path}. Put knowledge_base.txt beside chatbot.py.")
        self.raw = self.path.read_text(encoding="utf-8", errors="replace")
        self.sections = split_sections(self.raw)
        self.docs = []
        self.df = Counter()
        for title, body in self.sections:
            toks = words(title + " " + body)
            self.docs.append(toks)
            self.df.update(set(toks))
        self.avgdl = sum(map(len, self.docs)) / max(1, len(self.docs))
        self.sessions.clear()

    def _score(self, query, i):
        doc = self.docs[i]
        if not doc:
            return 0
        tf = Counter(doc)
        score = 0.0
        n = len(self.docs)
        for term in query:
            freq = tf[term]
            if not freq:
                continue
            df = self.df[term]
            idf = math.log(1 + (n - df + .5) / (df + .5))
            score += idf * (freq * 2.5) / (freq + 1.5 * (.25 + .75 * len(doc) / max(1, self.avgdl)))
        title = self.sections[i][0].lower()
        score += sum(.6 for t in set(query) if t in title)
        return score

    def retrieve(self, question, limit=5):
        q = expand(words(question))
        if not q:
            return []
        scored = [(self._score(q, i), i) for i in range(len(self.sections))]
        scored.sort(reverse=True)
        return [(s, *self.sections[i]) for s, i in scored[:limit] if s > 0]

    def _find_course(self, question, previous=None):
        q = norm(question)
        for course in COURSE_NAMES:
            c = norm(course)
            # Permit abbreviations and partial but distinctive course names.
            compact = c.replace(" ", "")
            if c in q or compact in q.replace(" ", ""):
                return course
        if previous and any(x in q for x in ("admission", "join", "apply", "eligibility", "fee", "seat", "documents")):
            return previous
        if "ai" in q and ("data" in q or "science" in q):
            return "B.Tech Artificial Intelligence and Data Science"
        return None

    def _clean_passage(self, body, max_chars=1100):
        lines = []
        for line in body.splitlines():
            line = line.strip()
            if not line:
                continue
            if re.fullmatch(r"[a-z0-9.-]+\.(com|edu|in|org)", line, re.I):
                continue
            if lines and line == lines[-1]:
                continue
            lines.append(line)
        result = "\n".join(lines)
        if len(result) > max_chars:
            cut = result[:max_chars].rsplit("\n", 1)[0]
            result = cut + "\n…"
        return result

    def get_response(self, message, session_id="default"):
        question = str(message or "").strip()
        if not question:
            return "Please type your question about Excel Engineering College."

        state = self.sessions.setdefault(str(session_id), {"course": None, "last_topic": None})
        lower = question.lower()
        q_words = set(words(question))

        contact = (
            "\n\nFor more details, please contact Excel Engineering College:\n"
            "Phone: +91 99655 23999\n"
            "Email: admission@excelcolleges.com"
        )
        fallback = (
            "Sorry, I couldn't find verified information about that in the college knowledge base."
            + contact
        )

        if re.search(r"\b(hi|hello|hey|good morning|good afternoon|good evening)\b", lower):
            return ("Hello! Welcome to Excel Engineering College. I can help with courses, "
                    "admissions, eligibility, fees, scholarships, departments, facilities, "
                    "hostel, placements, transport and contact information. What would you like to know?")
        if re.search(r"\b(thank you|thanks)\b", lower):
            return "You're welcome! I'm happy to help with your college enquiry."
        if re.search(r"\b(bye|goodbye)\b", lower):
            return "Thank you for visiting Excel Engineering College. Have a great day!"

        course = self._find_course(question, state.get("course"))
        if course:
            state["course"] = course

        # Topic-to-section routing: answer from the matching section only.
        topic_sections = [
            (r"\b(fee|fees|tuition|scholarship|scholarships|payment|cost)\b", "6. Fees and scholarships"),
            (r"\b(admission|admissions|apply|application|joining|join|eligibility|tnea|counselling|counseling)\b", "5. Admission information"),
            (r"\b(placement|placements|recruitment|career|training|internship|companies)\b", "9. Placement and training"),
            (r"\b(hostel|library|laborator|facilit|sports|internet|classroom|seminar)\b", "8. Campus facilities"),
            (r"\b(contact|phone|telephone|mobile|email|mail|office|principal|chairman|founder)\b", "14. Contact information"),
            (r"\b(address|location|located|where|directions|transport|bus|route)\b", "15. Transportation and location"),
            (r"\b(accreditation|approval|naac|nba|aicte|autonomous|affiliation|recognition)\b", "7. Accreditation and recognition"),
            (r"\b(research|innovation|entrepreneurship|incubation|patent)\b", "10. Research, innovation and entrepreneurship"),
            (r"\b(language|languages|foreign)\b", "11. Foreign language training"),
            (r"\b(student|activities|clubs|events|support|counselling cell)\b", "12. Student activities and support services"),
            (r"\b(exam|examination|results|result|syllabus|academic calendar|coe)\b", "16. Examination and academic information"),
            (r"\b(alumni|graduate|graduates)\b", "17. Alumni information"),
            (r"\b(vision|mission|objective|objectives)\b", "2. Vision and mission"),
            (r"\b(course|courses|programme|programmes|program|programs|degree|degrees)\b", "3. Courses offered"),
            (r"\b(department|departments|branch|branches|school)\b", "4. Departments"),
            (r"\b(college name|about the college|established|founded|campus|how old)\b", "1. College overview"),
        ]

        # A course-specific admission question should use the course context and admission section.
        if course and re.search(r"\b(admission|apply|join|joining|eligibility|tnea|fee|fees|documents)\b", lower):
            state["course"] = course

        for pattern, heading in topic_sections:
            if re.search(pattern, lower):
                section = next(((h, b) for h, b in self.sections if h.lower().startswith(heading.lower())), None)
                if section:
                    body = self._clean_passage(section[1], 1700)
                    # Fees are handled conservatively; do not fabricate a numerical amount.
                    if heading == "6. Fees and scholarships":
                        return (
                            "Excel Engineering College offers scholarship opportunities for eligible students. "
                            "The exact tuition fee depends on the course, government or management quota, "
                            "applicable fee regulations, scholarship eligibility, and hostel or transport needs. "
                            "The knowledge base does not contain a verified current fee amount, so I won't guess."
                            + contact
                        )
                    # Remove duplicated title from body and return only the matching topic section.
                    lines = body.splitlines()
                    if lines and lines[0].lower().startswith(heading.lower()):
                        body = "\n".join(lines[1:]).strip()
                    if not body:
                        return fallback
                    if course and heading == "5. Admission information":
                        return f"For **{course}**, here is the admission information available in the college knowledge base:\n\n{body}" + contact
                    return body + contact if heading in {
                        "5. Admission information", "9. Placement and training", "14. Contact information"
                    } else body

        # A named course can be looked up directly even when the visitor phrases it conversationally.
        if course:
            hits = self.retrieve(course, 5)
            relevant = [h for h in hits if course.lower() in h[2].lower()]
            if relevant:
                return self._clean_passage(relevant[0][2], 1300)

        # For other college-related queries, require actual overlap and a reasonable score.
        hits = self.retrieve(question, 5)
        if hits:
            best_score, heading, body = hits[0]
            query_terms = set(expand(words(question)))
            doc_terms = set(words(heading + " " + body))
            overlap = len(query_terms & doc_terms)
            if best_score >= 1.25 and overlap >= 1:
                # Return a single best passage, not a bundle of unrelated search results.
                answer = self._clean_passage(body, 1200)
                if answer and not re.search(r"\b(fee|fees|tuition|scholarship)\b", lower):
                    return answer
        return fallback

    def _select_topic(self, hits, keywords):
        for score, heading, body in hits:
            if any(k.lower() in (heading + " " + body[:500]).lower() for k in keywords):
                return self._clean_passage(body, 1000)
        return self._clean_passage(hits[0][2], 1000) if hits else "The knowledge base does not contain further admission details."

chatbot = OfflineCollegeBot()
print(f"Excel College offline assistant ready: {len(chatbot.sections)} knowledge sections loaded.")
