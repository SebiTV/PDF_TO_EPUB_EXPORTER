from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile


def _to_xhtml_paragraphs(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return "<p>Empty content.</p>"
    return "\n".join(f"<p>{line}</p>" for line in lines)


def write_simple_epub(output_file: Path, title: str, author: str, text: str) -> None:
    chapter_body = _to_xhtml_paragraphs(text)

    container_xml = """<?xml version=\"1.0\"?>
<container version=\"1.0\" xmlns=\"urn:oasis:names:tc:opendocument:xmlns:container\">
  <rootfiles>
    <rootfile full-path=\"OEBPS/content.opf\" media-type=\"application/oebps-package+xml\"/>
  </rootfiles>
</container>
"""

    content_opf = f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<package xmlns=\"http://www.idpf.org/2007/opf\" unique-identifier=\"bookid\" version=\"2.0\">
  <metadata xmlns:dc=\"http://purl.org/dc/elements/1.1/\">
    <dc:title>{title}</dc:title>
    <dc:creator>{author}</dc:creator>
    <dc:language>de</dc:language>
    <dc:identifier id=\"bookid\">urn:uuid:pdf-to-epub-exporter</dc:identifier>
  </metadata>
  <manifest>
    <item id=\"ncx\" href=\"toc.ncx\" media-type=\"application/x-dtbncx+xml\"/>
    <item id=\"chapter1\" href=\"chapter1.xhtml\" media-type=\"application/xhtml+xml\"/>
  </manifest>
  <spine toc=\"ncx\">
    <itemref idref=\"chapter1\"/>
  </spine>
</package>
"""

    toc_ncx = f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<ncx xmlns=\"http://www.daisy.org/z3986/2005/ncx/\" version=\"2005-1\">
  <head>
    <meta name=\"dtb:uid\" content=\"urn:uuid:pdf-to-epub-exporter\"/>
  </head>
  <docTitle>
    <text>{title}</text>
  </docTitle>
  <navMap>
    <navPoint id=\"navpoint-1\" playOrder=\"1\">
      <navLabel><text>Kapitel 1</text></navLabel>
      <content src=\"chapter1.xhtml\"/>
    </navPoint>
  </navMap>
</ncx>
"""

    chapter_xhtml = f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<html xmlns=\"http://www.w3.org/1999/xhtml\">
  <head>
    <title>{title}</title>
  </head>
  <body>
    <h1>{title}</h1>
    {chapter_body}
  </body>
</html>
"""

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output_file, "w") as epub:
        epub.writestr("mimetype", "application/epub+zip", compress_type=ZIP_STORED)
        epub.writestr("META-INF/container.xml", container_xml, compress_type=ZIP_DEFLATED)
        epub.writestr("OEBPS/content.opf", content_opf, compress_type=ZIP_DEFLATED)
        epub.writestr("OEBPS/toc.ncx", toc_ncx, compress_type=ZIP_DEFLATED)
        epub.writestr("OEBPS/chapter1.xhtml", chapter_xhtml, compress_type=ZIP_DEFLATED)
