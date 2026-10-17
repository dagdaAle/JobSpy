"""Local, deterministic CV layout. Imported text and Markdown share the same template."""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from html import escape
from pathlib import Path

import reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Flowable, Paragraph, Table, TableStyle

TEMPLATES = {"europass", "classic"}
BLUE = colors.HexColor("#07558b")
INK = colors.HexColor("#283542")
for name, filename in [("CVSans", "Vera.ttf"), ("CVSans-Bold", "VeraBd.ttf"),
                       ("CVSans-Italic", "VeraIt.ttf"), ("CVSans-BoldItalic", "VeraBI.ttf")]:
    if name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(name, str(Path(reportlab.__file__).parent / "fonts" / filename)))
pdfmetrics.registerFontFamily("CVSans", normal="CVSans", bold="CVSans-Bold", italic="CVSans-Italic", boldItalic="CVSans-BoldItalic")

SIDE = {"competenze", "competenze tecniche", "competenze digitali", "technical skills", "skills", "digital skills",
        "lingue", "competenze linguistiche", "languages", "language skills"}
HEADINGS = SIDE | {"profilo", "profile", "about me", "informazioni personali", "professional summary",
    "esperienza", "esperienze", "esperienza lavorativa", "esperienze lavorative", "experience", "work experience", "professional experience",
    "istruzione", "istruzione e formazione", "education", "education and training", "education & training", "formazione",
    "didattica e formazione erogata", "teaching", "progetti", "projects", "certificazioni", "certifications"}
DATE = re.compile(r"(?:\d{1,2}/)?\d{1,2}/\d{4}|\b(?:19|20)\d{2}\b")
BULLET = re.compile(r"^(?:[-*•▪●]|\d+[.)])\s+")


@dataclass
class Section:
    title: str
    blocks: list[tuple[str, str]] = field(default_factory=list)


def plain(text):
    return re.sub(r"[*_`]", "", text).strip()


def parse(text):
    """Preserve facts and section order; recognize headings without a model call."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").strip().splitlines()
    if not lines:
        raise ValueError("Il CV è vuoto")
    name = plain(re.sub(r"^#+\s*", "", lines.pop(0).strip()))
    header, sections, current, blank = [], [], None, True
    for raw in lines:
        line = raw.strip()
        if not line:
            blank = True
            continue
        heading = re.match(r"^#{1,2}\s+(.+)$", line)
        label = plain(line).rstrip(":")
        is_heading = heading or label.lower() in HEADINGS or (
            not BULLET.match(line) and label.isupper() and 6 <= len(label) <= 65
            and len(label.split()) >= 2 and not re.search(r"[\d@|]", label))
        if is_heading:
            current = Section(plain(heading.group(1)) if heading else label)
            sections.append(current)
        elif current is None:
            header.append(plain(line))
        else:
            bullet = BULLET.match(line)
            if bullet:
                current.blocks.append(("bullet", line[bullet.end():]))
            elif line.startswith("### "):
                current.blocks.append(("entry", line[4:]))
            elif DATE.search(line):
                current.blocks.append(("entry", line))
            elif "|" in line:
                current.blocks.append(("organization", line))
            elif not blank and current.blocks and current.blocks[-1][0] == "bullet" and not re.match(r"^[\w /&+-]{2,45}:", line):
                kind, prior = current.blocks[-1]
                current.blocks[-1] = kind, prior + " " + line
            elif not blank and current.blocks and current.blocks[-1][0] == "body" and not re.match(r"^[^:]{2,45}:", line):
                kind, prior = current.blocks[-1]
                current.blocks[-1] = kind, prior + " " + line
            else:
                current.blocks.append(("body", line))
        blank = False
    return name, header, sections


def inline(text):
    # Escape all user HTML: no remote resources or executable markup in PDFs.
    text = escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return re.sub(r"\[([^]]+)\]\(([^)]+)\)", r"\1 (\2)", text)


class Heading(Flowable):
    def __init__(self, title, style, classic):
        super().__init__()
        self.paragraph = Paragraph(inline(title.upper() if classic else title[:1].upper() + title[1:].lower()), style)
        self.classic, self.keepWithNext = classic, True
        self.spaceBefore = 10

    def wrap(self, width, height):
        self.width = width
        _, h = self.paragraph.wrap(width, height)
        self.height = h + (9 if self.classic else 7)
        return width, self.height

    def draw(self):
        self.paragraph.drawOn(self.canv, 0, self.height - self.paragraph.height)
        if self.classic:
            self.canv.setStrokeColor(BLUE)
            self.canv.setLineWidth(0.6)
            self.canv.line(0, 4, self.width, 4)


def styles(size):
    body = ParagraphStyle("body", fontName="CVSans", fontSize=size, leading=size * 1.36,
                          textColor=INK, spaceAfter=3, splitLongWords=True)
    return {"body": body,
        "bullet": ParagraphStyle("bullet", parent=body, leftIndent=10, bulletIndent=1, spaceAfter=2),
        "entry": ParagraphStyle("entry", parent=body, fontName="CVSans-Bold", spaceBefore=5, spaceAfter=2, keepWithNext=True),
        "organization": ParagraphStyle("organization", parent=body, fontName="CVSans-Italic", textColor=colors.HexColor("#56616d"), spaceAfter=4, keepWithNext=True),
        "heading": ParagraphStyle("heading", parent=body, fontName="CVSans-Bold", textColor=BLUE, fontSize=size + 1.4, leading=size * 1.45, spaceBefore=10)}


def flowables(sections, width, s, classic):
    result = []
    for section in sections:
        result.append(Heading(section.title, s["heading"], classic))
        for kind, text in section.blocks:
            match = DATE.search(plain(text)) if kind == "entry" else None
            if match and match.start() > 3:
                title, dates = plain(text)[:match.start()].strip(), plain(text)[match.start():].strip()
                if title and len(dates) < 55:
                    date_style = ParagraphStyle("date", parent=s["body"], fontSize=s["body"].fontSize - 0.4, alignment=2)
                    date_width = min(105, width * 0.34)
                    row = Table([[Paragraph(inline(title), s["entry"]), Paragraph(inline(dates), date_style)]], colWidths=[width - date_width, date_width])
                    row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
                    row.keepWithNext = True
                    result.append(row)
                    continue
            if kind == "body" and re.match(r"^[^:]{2,45}:", text):
                label, rest = text.split(":", 1)
                markup = "<b>" + inline(label) + ":</b>" + inline(rest)
            else:
                markup = inline(text)
            result.append(Paragraph(markup, s[kind], bulletText="•" if kind == "bullet" else None))
    return result


def column(canv, story, x, top, bottom, width):
    remaining, y = list(story), top
    while remaining:
        item = remaining[0]
        before = item.getSpaceBefore() if y < top else 0
        _, height = item.wrap(width, y - bottom)
        after = item.getSpaceAfter()
        needed = before + height
        if item.getKeepWithNext():
            # Keep heading + role + employer with the start of the first bullet.
            previous, index = item, 1
            while previous.getKeepWithNext() and index < len(remaining):
                following = remaining[index]
                _, next_h = following.wrap(width, top - bottom)
                needed += previous.getSpaceAfter() + following.getSpaceBefore()
                needed += next_h if following.getKeepWithNext() else min(next_h, 26)
                previous, index = following, index + 1
        if needed > y - bottom:
            if not item.getKeepWithNext():
                pieces = item.split(width, max(0, y - bottom - before))
                if len(pieces) > 1:
                    remaining[:1] = pieces
                    continue
            break
        item.drawOn(canv, x, y - before - height)
        y -= before + height + after
        remaining.pop(0)
    return remaining


def render(document, template, size):
    name, header, sections = document
    out = io.BytesIO()
    canv = canvas.Canvas(out, pagesize=A4, pageCompression=1)
    canv.setTitle(name + " - Curriculum vitae")
    canv.setAuthor(name)
    w, h = A4
    classic = template == "classic"
    margin = 45 if classic else 34
    full_width, s = w - margin * 2, styles(size)
    title = Paragraph(inline(name), ParagraphStyle("name", fontName="CVSans-Bold", fontSize=20, leading=24, textColor=BLUE))
    _, title_h = title.wrap(full_width, h)
    header_y, header_items = h - 43 - title_h - 7, []
    for i, line in enumerate(header):
        role = i == 0 and "@" not in line and not re.search(r"\+?\d{6,}", line)
        style = ParagraphStyle("contact", parent=s["body"], fontSize=10 if role else 8.2, leading=12 if role else 11)
        p = Paragraph(inline(line), style)
        _, ph = p.wrap(full_width, h)
        header_items.append((p, ph))
        header_y -= ph + 3
    content_top = header_y - 13
    if content_top < 150:
        raise ValueError("Inserisci titoli di sezione per separare intestazione e contenuti del CV")
    side = [section for section in sections if section.title.lower() in SIDE] if not classic else []
    main = [section for section in sections if section not in side]
    side_w = 143
    main_x = margin if classic else margin + side_w + 25
    main_w = w - margin - main_x
    main_story = flowables(main, main_w, s, classic)
    side_story = flowables(side, side_w - 15, styles(size - 0.2), False)
    pages = 0
    while main_story or side_story or pages == 0:
        pages += 1
        if pages == 1:
            title.drawOn(canv, margin, h - 43 - title_h)
            y = h - 43 - title_h - 7
            for p, ph in header_items:
                p.drawOn(canv, margin, y - ph)
                y -= ph + 3
            top = content_top
        else:
            canv.setFont("CVSans-Bold", 10); canv.setFillColor(BLUE)
            canv.drawString(margin, h - 33, name)
            top = h - 55
        if not classic:
            canv.setFillColor(colors.HexColor("#f1f6fa"))
            canv.roundRect(margin - 9, 36, side_w + 4, top - 30, 7, stroke=0, fill=1)
        before = list(main_story), list(side_story)
        main_story = column(canv, main_story, main_x, top, 43, main_w)
        side_story = column(canv, side_story, margin, top, 46, side_w - 15)
        if before == (main_story, side_story) and (main_story or side_story):
            raise ValueError("Un blocco del CV è troppo grande: dividilo in paragrafi più brevi")
        if pages > 1 or main_story or side_story:
            canv.setFillColor(colors.HexColor("#8795a1")); canv.setFont("CVSans", 7)
            canv.drawRightString(w - margin, 23, str(pages))
        canv.showPage()
    canv.save()
    return out.getvalue(), pages


def to_pdf(text, template="europass"):
    if template not in TEMPLATES:
        raise ValueError("Template CV non valido")
    document = parse(text)
    result, pages = render(document, template, 9.1)
    if pages == 2:
        for size in (8.7, 8.3):
            candidate, candidate_pages = render(document, template, size)
            if candidate_pages == 1:
                return candidate
    return result
