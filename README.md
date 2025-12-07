# Substack Scraper

Tools to scrape articles from a Substack publication and convert them into Markdown for a Hugo website.

## Prerequisites

- Python 3
- `substack-api` library

```bash
pip install substack-api
```

## Usage

### 1. Scrape an Article

Use `scrape_substack.py` to fetch an article by its URL. This saves the raw content and metadata to a JSON file in the `scraped_data` directory.

```bash
python3 scrape_substack.py <SUBSTACK_ARTICLE_URL>
```

**Example:**
```bash
python3 scrape_substack.py https://{your_substack_url}.substack.com/p/{your_article_id}
```

### 2. Process to Markdown

Use `process_letter_json.py` to convert the scraped JSON files (in `scraped_data`) into Hugo-ready Markdown files (in `content/posts/letters`). this script handles cleaning HTML, removing widgets, and formatting the frontmatter.

```bash
python3 process_letter_json.py scraped_data
```

## Agent Prompt

If you are using an AI agent (like Cursor or similar) and want to automate this flow, you can use the following prompt:

> **Task:** Scrape and process this Substack article: `[INSERT_URL_HERE]`
>
> **Steps:**
> 1. Run `python3 scripts/substack_scraper/scrape_substack.py [INSERT_URL_HERE]` to fetch the data.
> 2. Run `python3 scripts/substack_scraper/process_letter_json.py scraped_data` to convert it to Markdown.
> 3. Verify the generated markdown file in `content/posts/letters/`.