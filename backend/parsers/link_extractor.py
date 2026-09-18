import logging
from typing import Dict, Any
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 SecondSelf/1.0"
)

async def parse_url(url: str) -> Dict[str, Any]:
    """
    Async HTTP fetch with 8.0s timeout and multi-tier content extraction:
    Tier 1: trafilatura main body extractor (strips ads, sidebars, headers).
    Tier 2: BeautifulSoup OpenGraph metadata + paragraph aggregator fallback.
    """
    cleaned_url = url.strip()
    if not cleaned_url.startswith("http://") and not cleaned_url.startswith("https://"):
        cleaned_url = f"https://{cleaned_url}"

    headers = {"User-Agent": USER_AGENT}
    html_content = ""
    status_code = 0

    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True, verify=False) as client:
            resp = await client.get(cleaned_url, headers=headers)
            status_code = resp.status_code
            html_content = resp.text
    except httpx.TimeoutException:
        logger.error(f"HTTP request timed out after 8.0s for {cleaned_url}")
        raise TimeoutError(f"Web extraction timed out for {cleaned_url} (8.0s limit reached)")
    except Exception as e:
        logger.error(f"HTTP fetch failed for {cleaned_url}: {e}")
        raise RuntimeError(f"Could not connect to URL {cleaned_url}: {e}")

    extracted_body = ""
    title = cleaned_url

    # 1. Try Trafilatura for clean body extraction
    try:
        import trafilatura
        trafilatura_text = trafilatura.extract(
            html_content,
            include_links=True,
            include_images=False,
            include_tables=True,
            output_format="txt"
        )
        if trafilatura_text and len(trafilatura_text.strip()) > 50:
            extracted_body = trafilatura_text.strip()
    except Exception as e:
        logger.debug(f"Trafilatura extraction skipped ({e})")

    # 2. BeautifulSoup OpenGraph metadata & paragraph extraction fallback
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Extract Title
    og_title = soup.find("meta", property="og:title")
    title_tag = soup.find("title")
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()
    elif title_tag and title_tag.text:
        title = title_tag.text.strip()

    # Extract OpenGraph Description
    og_desc = soup.find("meta", property="og:description")
    meta_desc = soup.find("meta", attrs={"name": "description"})
    summary = ""
    if og_desc and og_desc.get("content"):
        summary = og_desc["content"].strip()
    elif meta_desc and meta_desc.get("content"):
        summary = meta_desc["content"].strip()

    # If trafilatura was empty, gather paragraph text
    if not extracted_body:
        paragraphs = [p.get_text().strip() for p in soup.find_all("p") if len(p.get_text().strip()) > 20]
        if paragraphs:
            extracted_body = "\n\n".join(paragraphs)
        elif summary:
            extracted_body = summary
        else:
            extracted_body = f"[Web Page: {cleaned_url} (No readable text body extracted from HTML)]"

    full_text = f"# {title}\n\n**Source URL:** {cleaned_url}\n\n{extracted_body}"

    metadata = {
        "url": cleaned_url,
        "http_status": status_code,
        "summary": summary,
        "format": "WEB_LINK"
    }

    return {
        "text": full_text,
        "title": title,
        "url": cleaned_url,
        "metadata": metadata
    }
