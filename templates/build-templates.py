#!/usr/bin/env python3
"""Build the three Pandoc reference documents used for Word output.

    memo-reference.docx   supporting documents (memoranda, outline, summary, tables)
    brief-reference.docx  the sponsor brief (memo look, slightly tighter)
    bill-reference.docx   the proposed statutory language (Ohio pre-introduction draft look)

Run once (or after changing a setting below):  python3 templates/build-templates.py
All text is black. Margins are 1 inch. Footers carry page numbers.
"""
import os, re, subprocess, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'

PROFILES = {
    "memo": dict(font="Times New Roman", body=12, title=17, h2=13.5, h3=12, h4=12,
                 after=120, line=264, foot=10, table=10.5,
                 footer="Page {PAGE} of {NUMPAGES}"),
    "brief": dict(font="Times New Roman", body=11, title=17, h2=13, h3=12, h4=11,
                  after=60, line=240, foot=9, table=10, hgap=0.5,
                  footer="Page {PAGE} of {NUMPAGES}"),
    "bill": dict(font="Courier New", body=12, title=12, h2=12, h3=12, h4=12,
                 after=0, line=480, foot=10, table=10, bill=True,
                 footer="Pre-introduction draft — not introduced — Page {PAGE}"),
}


def hp(pt):
    return str(int(round(pt * 2)))


def rpr(font=None, size=None, bold=False, italic=False, extra=""):
    out = "<w:rPr>"
    if font:
        out += f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:eastAsia="{font}" w:cs="{font}"/>'
    if bold:
        out += "<w:b/><w:bCs/>"
    if italic:
        out += "<w:i/><w:iCs/>"
    out += '<w:color w:val="000000"/>'
    if size:
        out += f'<w:sz w:val="{hp(size)}"/><w:szCs w:val="{hp(size)}"/>'
    return out + extra + "</w:rPr>"


def pstyle(sid, name, ppr="", rp="", based="Normal", nxt=None, custom=False, q=True):
    c = ' w:customStyle="1"' if custom else ""
    n = f'<w:next w:val="{nxt}"/>' if nxt else ""
    b = f'<w:basedOn w:val="{based}"/>' if based else ""
    return (f'<w:style w:type="paragraph"{c} w:styleId="{sid}"><w:name w:val="{name}"/>{b}{n}'
            f'{"<w:qFormat/>" if q else ""}<w:pPr>{ppr}</w:pPr>{rp}</w:style>')


def cstyle(sid, name, rp, based="DefaultParagraphFont"):
    return (f'<w:style w:type="character" w:customStyle="1" w:styleId="{sid}"><w:name w:val="{name}"/>'
            f'<w:basedOn w:val="{based}"/>{rp}</w:style>')


def styles_xml(p):
    f, a, ln = p["font"], p["after"], p["line"]
    sp = lambda before, after, line=ln: f'<w:spacing w:before="{before}" w:after="{after}" w:line="{line}" w:lineRule="auto"/>'
    keep = "<w:keepNext/><w:keepLines/>"
    g = lambda twips: int(twips * p.get("hgap", 1.0))  # space above headings
    body_ind = '<w:ind w:firstLine="720"/>' if p.get("bill") else ""
    s = [f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles {W}>',
         '<w:docDefaults><w:rPrDefault>' + rpr(f, p["body"], extra='<w:lang w:val="en-US"/>') + '</w:rPrDefault>'
         f'<w:pPrDefault><w:pPr>{sp(0, a)}</w:pPr></w:pPrDefault></w:docDefaults>',
         pstyle("Normal", "Normal", based=None),
         '<w:style w:type="character" w:default="1" w:styleId="DefaultParagraphFont"><w:name w:val="Default Paragraph Font"/><w:uiPriority w:val="1"/><w:semiHidden/></w:style>',
         pstyle("BodyText", "Body Text", sp(0, a) + body_ind),
         pstyle("FirstParagraph", "First Paragraph", "", based="BodyText", nxt="BodyText", custom=True),
         pstyle("Compact", "Compact", sp(0, 30 if not p.get("bill") else 0), based="BodyText", custom=True),
         pstyle("Title", "Title", keep + sp(0, 160, 240), rpr(f, p["title"], bold=True), nxt="BodyText"),
         pstyle("Subtitle", "Subtitle", keep + sp(0, 160, 240), rpr(f, p["h2"], bold=True), nxt="BodyText"),
         pstyle("Author", "Author", sp(0, 60), custom=True),
         pstyle("Date", "Date", sp(0, 160)),
         pstyle("AbstractTitle", "Abstract Title", keep + sp(120, 60), rpr(f, p["body"], bold=True), custom=True),
         pstyle("Abstract", "Abstract", sp(0, a), custom=True),
         pstyle("Bibliography", "Bibliography", sp(0, a), custom=True),
         pstyle("Heading1", "heading 1", keep + sp(0, 160, 240) + '<w:outlineLvl w:val="0"/>', rpr(f, p["title"], bold=True), nxt="BodyText"),
         pstyle("Heading2", "heading 2", keep + sp(g(240), 80, 240) + '<w:outlineLvl w:val="1"/>', rpr(f, p["h2"], bold=True), nxt="BodyText"),
         pstyle("Heading3", "heading 3", keep + sp(g(200), 60, 240) + '<w:outlineLvl w:val="2"/>', rpr(f, p["h3"], bold=True), nxt="BodyText"),
         pstyle("Heading4", "heading 4", keep + sp(g(160), 40, 240) + '<w:outlineLvl w:val="3"/>', rpr(f, p["h4"], bold=True, italic=True), nxt="BodyText"),
         ]
    for i in range(5, 10):
        s.append(pstyle(f"Heading{i}", f"heading {i}", keep + sp(120, 40, 240) + f'<w:outlineLvl w:val="{i-1}"/>',
                        rpr(f, p["h4"], bold=True), nxt="BodyText"))
    s += [
        pstyle("BlockText", "Block Text", sp(60, a) + '<w:ind w:left="567" w:right="567"/>', nxt="BodyText"),
        pstyle("FootnoteText", "footnote text", sp(0, 20, 240), rpr(f, p["foot"])),
        pstyle("FootnoteBlockText", "Footnote Block Text", sp(0, 20, 240), rpr(f, p["foot"]), based="FootnoteText", custom=True),
        pstyle("DefinitionTerm", "Definition Term", keep + sp(60, 0), rpr(bold=True), custom=True),
        pstyle("Definition", "Definition", sp(0, a), custom=True),
        pstyle("Caption", "caption", sp(60, 120), rpr(f, p["foot"], italic=True)),
        pstyle("TableCaption", "Table Caption", sp(60, 60), rpr(f, p["foot"], italic=True), based="Caption", custom=True),
        pstyle("ImageCaption", "Image Caption", sp(60, 60), rpr(f, p["foot"], italic=True), based="Caption", custom=True),
        pstyle("Figure", "Figure", "", custom=True),
        pstyle("CaptionedFigure", "Captioned Figure", keep, based="Figure", custom=True),
        pstyle("TOCHeading", "TOC Heading", keep + sp(0, 160, 240), rpr(f, p["h2"], bold=True), based="Heading1", nxt="BodyText"),
        cstyle("BodyTextChar", "Body Text Char", "<w:rPr/>"),
        cstyle("VerbatimChar", "Verbatim Char", rpr("Courier New", p["body"] - 1)),
        cstyle("SectionNumber", "Section Number", "<w:rPr/>"),
        cstyle("FootnoteReference", "footnote reference", '<w:rPr><w:vertAlign w:val="superscript"/></w:rPr>'),
        cstyle("Hyperlink", "Hyperlink", rpr()),
        # Tables: thin black grid, compact cell text.
        ('<w:style w:type="table" w:default="1" w:styleId="Table"><w:name w:val="Table"/><w:qFormat/>'
         '<w:pPr><w:spacing w:before="20" w:after="20" w:line="240" w:lineRule="auto"/></w:pPr>'
         f'{rpr(f, p["table"])}'
         '<w:tblPr><w:tblInd w:w="0" w:type="dxa"/><w:tblBorders>'
         + "".join(f'<w:{e} w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
                   for e in ("top", "left", "bottom", "right", "insideH", "insideV"))
         + '</w:tblBorders><w:tblCellMar><w:top w:w="29" w:type="dxa"/><w:left w:w="86" w:type="dxa"/>'
           '<w:bottom w:w="29" w:type="dxa"/><w:right w:w="86" w:type="dxa"/></w:tblCellMar></w:tblPr>'
           '<w:tblStylePr w:type="firstRow"><w:rPr><w:b/><w:bCs/></w:rPr>'
           '<w:tcPr><w:shd w:val="clear" w:color="auto" w:fill="E7E6E6"/></w:tcPr></w:tblStylePr></w:style>'),
    ]
    if p.get("bill"):
        s += [
            pstyle("DraftBanner", "Draft Banner",
                   '<w:pBdr><w:top w:val="single" w:sz="6" w:space="4" w:color="000000"/>'
                   '<w:bottom w:val="single" w:sz="6" w:space="4" w:color="000000"/></w:pBdr>'
                   '<w:suppressLineNumbers/>' + sp(0, 60, 240) + '<w:jc w:val="center"/>',
                   rpr("Arial", 9, bold=True), custom=True),
            pstyle("BillHeading", "Bill Heading", sp(480, 240, 240) + '<w:jc w:val="center"/>', rpr(bold=True), custom=True),
            pstyle("BillTitle", "Bill Title", sp(0, 480) + '<w:ind w:left="1440" w:right="720"/>', custom=True),
            pstyle("EnactingClause", "Enacting Clause", sp(240, 480, 240) + '<w:jc w:val="center"/>', rpr(bold=True), custom=True),
        ]
    s.append("</w:styles>")
    return "".join(s)


def footer_xml(p):
    run = lambda inner: f'<w:r>{rpr("Arial" if p.get("bill") else p["font"], 9)}{inner}</w:r>'
    parts = []
    for i, chunk in enumerate(re.split(r"\{(PAGE|NUMPAGES)\}", p["footer"])):
        if i % 2 == 0:
            if chunk:
                parts.append(run(f'<w:t xml:space="preserve">{chunk}</w:t>'))
        else:
            parts += [run('<w:fldChar w:fldCharType="begin"/>'),
                      run(f'<w:instrText xml:space="preserve"> {chunk} </w:instrText>'),
                      run('<w:fldChar w:fldCharType="separate"/>'), run("<w:t>1</w:t>"),
                      run('<w:fldChar w:fldCharType="end"/>')]
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr {W}><w:p><w:pPr>'
            f'<w:suppressLineNumbers/><w:jc w:val="center"/></w:pPr>{"".join(parts)}</w:p></w:ftr>')


def build(name, p):
    base = subprocess.run(["pandoc", "--print-default-data-file", "reference.docx"],
                          check=True, capture_output=True).stdout
    tmp = os.path.join(HERE, f".{name}-base.docx")
    open(tmp, "wb").write(base)
    zin = zipfile.ZipFile(tmp)
    out = os.path.join(HERE, f"{name}-reference.docx")
    zout = zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED)
    R = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
    for item in zin.infolist():
        data = zin.read(item.filename)
        if item.filename == "word/styles.xml":
            data = styles_xml(p).encode()
        elif item.filename == "word/document.xml":
            ln = '<w:lnNumType w:countBy="1" w:distance="360" w:restart="continuous"/>' if p.get("bill") else ""
            data = data.decode().replace(
                "<w:sectPr />",
                f'<w:sectPr><w:footerReference {R} w:type="default" r:id="rIdRefFooter"/>'
                '<w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" '
                f'w:left="1440" w:header="720" w:footer="576" w:gutter="0"/>{ln}</w:sectPr>').encode()
        elif item.filename == "word/_rels/document.xml.rels":
            data = data.decode().replace("</Relationships>",
                '<Relationship Id="rIdRefFooter" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                'relationships/footer" Target="footer1.xml"/></Relationships>').encode()
        elif item.filename == "[Content_Types].xml":
            data = data.decode().replace("</Types>",
                '<Override PartName="/word/footer1.xml" ContentType="application/'
                'vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/></Types>').encode()
        zout.writestr(item, data)
    zout.writestr("word/footer1.xml", footer_xml(p))
    zout.close()
    os.remove(tmp)
    print("wrote", os.path.relpath(out))


if __name__ == "__main__":
    for name, p in PROFILES.items():
        build(name, p)
