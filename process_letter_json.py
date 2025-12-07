
import json
import os
import re
import sys
from datetime import datetime

def process_letters(scraped_dir, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    files = [f for f in os.listdir(scraped_dir) if f.endswith('.json')]
    
    for filename in files:
        file_path = os.path.join(scraped_dir, filename)
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        # Data structure expected:
        # {
        #   "id": "031",
        #   "url": "...",
        #   "title": "...",
        #   "date": "2024-01-01T...",
        #   "headerHTML": "...",
        #   "bodyHTML": "..."
        # }
        
        letter_id = data.get('id')
        title = data.get('title')
        date = data.get('date')
        header_html = data.get('headerHTML', '')
        body_html = data.get('bodyHTML', '')
        # Try to extract date from LD-JSON in headerHTML (Preferred source)
        # Look for <script type="application/ld+json">...</script>
        ld_json_match = re.search(r'<script type="application/ld\+json">(.*?)</script>', header_html, re.DOTALL)
        if ld_json_match:
            try:
                ld_data = json.loads(ld_json_match.group(1))
                if 'datePublished' in ld_data:
                    date = ld_data['datePublished']
            except json.JSONDecodeError:
                pass

        # Fallback date extraction if still missing (or override if simpler regex failed?)
        # Actually, LD-JSON is most reliable. usage above will set 'date' if found.
        
        # If date is missing or we suspect it's wrong (fallback to visible date)
        # 031 has no ld+json but has visible date "Sep 14, 2025"
        if not date or (letter_id == '031' and '2021' in str(date)):
            # Try to find visible date in header, e.g. >Sep 14, 2025<
            # This is a common pattern in Substack headers
            visible_date_match = re.search(r'>([A-Z][a-z]{2} \d{1,2}, \d{4})<', header_html)
            if visible_date_match:
                date_str = visible_date_match.group(1)
                try:
                    dt = datetime.strptime(date_str, '%b %d, %Y')
                    date = dt.strftime('%Y-%m-%dT%H:%M:%S+00:00')
                    print(f"Extracted visible date for {letter_id}: {date}")
                except Exception as e:
                    print(f"Failed to parse visible date {date_str}: {e}")

        if not date:
            # Try to find "post_date" in body_html (often in window._preloads)
            # Pattern: \"post_date\":\"2025-02-03T06:33:11.926Z\"
            # Must match explicit quote before post_date to distinguish from first_post_date
            date_match = re.search(r'\\?"post_date\\?"\s*:\s*\\?"([\d-]+)', body_html)
            if date_match:
                date = date_match.group(1)
        
        # Determine if we should update the JSON file
        original_date = data.get('date')
        # If we extracted a new date, or if it differs meaningfully (keeping simple check)
        if date and original_date != date:
            print(f"Updating JSON for {letter_id}: {original_date} -> {date}")
            data['date'] = date
            try:
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2)
            except Exception as e:
                print(f"Failed to update JSON for {letter_id}: {e}")



        substack_url = data.get('url')
        
        # Clean Header
        h3_match = re.search(r'<h3[^>]*>(.*?)</h3>', header_html, re.DOTALL)
        clean_header = ""
        if h3_match:
            subtitle_text = h3_match.group(1)
            clean_header += f'<h4 class="subtitle"><a href="{substack_url}" target="_blank">{subtitle_text}</a></h4>\n'
            
        # Clean Body
        # Remove <figure>...</figure> blocks
        clean_body = re.sub(r'<figure[\s\S]*?</figure>', '', body_html)
        # Remove standalone <img> tags
        clean_body = re.sub(r'<img[^>]*>', '', clean_body)
        # Remove <picture>...</picture> tags
        clean_body = re.sub(r'<picture[\s\S]*?</picture>', '', clean_body)
        
        # Remove Substack "subscribe" or "share" buttons/widgets (post-ufi)
        clean_body = re.sub(r'<div[^>]*class="[^"]*post-ufi[^"]*"[\s\S]*?</div>', '', clean_body)
        # Remove "Share this post" or "Subscribe" buttons often found in footer-like divs
        clean_body = re.sub(r'<div[^>]*class="[^"]*subscription-widget[^"]*"[\s\S]*?</div>', '', clean_body)
        
        # Remove Footer and everything after (robust regex)
        # Matches <div class="footer-wrap publication-footer">... EOF
        clean_body = re.sub(r'<div[^>]*class="[^"]*footer-wrap publication-footer[^"]*"[\s\S]*', '', clean_body)
        
        # Remove post-footer (social buttons at end of article)
        clean_body = re.sub(r'<div[^>]*class="[^"]*post-footer[^"]*"[\s\S]*?</div>', '', clean_body)

                
        # Remove all scripts
        clean_body = re.sub(r'<script[\s\S]*?</script>', '', clean_body)

        # Remove <button> tags (specific link buttons)
        clean_body = re.sub(r'<button[^>]*aria-label="Link"[^>]*>[\s\S]*?</button>', '', clean_body)
        
        # Helper to remove balanced divs
        def find_balanced_div_range(html, class_pattern=None, attr_pattern=None, start_search_pos=0):
            # Construct search pattern
            pattern = r'<div[^>]*'
            if class_pattern:
                pattern += f'class="[^"]*{class_pattern}[^"]*"'
            if attr_pattern:
                pattern += f'{attr_pattern}'
            
            match = re.search(pattern, html[start_search_pos:])
            if not match:
                return None
            
            start_idx = start_search_pos + match.start()
            # Now scan for balanced end
            depth = 0
            
            # Simple scan
            found_end = False
            in_quote = False
            quote_char = ''
            
            i = start_idx
            while i < len(html):
                if in_quote:
                    if html[i] == quote_char:
                        in_quote = False
                elif html[i] == '"' or html[i] == "'":
                    in_quote = True
                    quote_char = html[i]
                elif html[i] == '<':
                    if html[i+1:i+4].lower() == 'div':
                         char_after = html[i+4]
                         if char_after == '>' or char_after.isspace():
                             depth += 1
                    elif html[i+1:i+5].lower() == '/div':
                         char_after = html[i+5]
                         if char_after == '>' or char_after.isspace():
                             depth -= 1
                             if depth == 0:
                                 end_idx = html.find('>', i) + 1
                                 return (start_idx, end_idx)
                i += 1
            return None

        def remove_balanced_div(html, class_pattern=None, attr_pattern=None):
            while True:
                r = find_balanced_div_range(html, class_pattern, attr_pattern)
                if not r:
                    break
                html = html[:r[0]] + html[r[1]:]
            return html
            
        def extract_balanced_div(html, class_pattern=None):
            r = find_balanced_div_range(html, class_pattern)
            if r:
                return html[r[0]:r[1]]
            return None

        # 1. Extract MAIN content (safe list)
        # This drops all footer siblings (Comments, Read More, Top Posts etc)
        main_content = extract_balanced_div(clean_body, class_pattern="available-content")
        if main_content:
            clean_body = main_content
        
        # 2. Clean INTERNALS (widgets inside the article)
        
        # Remove "subscribe-widget" divs (nested)
        clean_body = remove_balanced_div(clean_body, class_pattern="subscribe-widget")
        
        # Remove buttons with "post-ufi-button" class (comments, share, etc.)
        clean_body = re.sub(r'<button[^>]*class="[^"]*post-ufi-button[^"]*"[\s\S]*?</button>', '', clean_body)

        # Remove "post-ufi" container if present in body (often contains the buttons)
        clean_body = remove_balanced_div(clean_body, class_pattern="post-ufi")
        
        # Remove "visibility-check"
        clean_body = remove_balanced_div(clean_body, class_pattern="visibility-check")

        # Remove comments section (double check if inside)
        clean_body = remove_balanced_div(clean_body, class_pattern="comments-section")
        
        # Remove other single-post-sections (like Top Posts Footer)
        clean_body = remove_balanced_div(clean_body, class_pattern="single-post-section")
        
        # Remove "Ready for more?" footer (pubInvertedTheme)
        clean_body = remove_balanced_div(clean_body, class_pattern="pubInvertedTheme")

        # Remove empty captioned-image-container
        clean_body = re.sub(r'<div class="captioned-image-container">\s*</div>', '', clean_body)

        # Remove "subscription-widget-wrap-editor"
        clean_body = remove_balanced_div(clean_body, class_pattern="subscription-widget-wrap-editor")

        def unwrap_balanced_div(html, class_pattern=None):
            while True:
                r = find_balanced_div_range(html, class_pattern)
                if not r:
                    break
                div_content = html[r[0]:r[1]]
                
                # Find the end of the opening tag respecting quotes
                tag_end_idx = -1
                in_quote = False
                quote_char = ''
                for i, char in enumerate(div_content):
                    if in_quote:
                        if char == quote_char:
                            in_quote = False
                    elif char == '"' or char == "'":
                        in_quote = True
                        quote_char = char
                    elif char == '>':
                        tag_end_idx = i
                        break
                
                if tag_end_idx != -1 and len(div_content) > 6:
                     inner = div_content[tag_end_idx+1:-6]
                     html = html[:r[0]] + inner + html[r[1]:]
                else:
                     # Fallback: just remove it if malformed
                     html = html[:r[0]] + html[r[1]:]
            return html

        # Unwrap "embedded-post-wrap" to just show the link/card structure simply
        clean_body = unwrap_balanced_div(clean_body, class_pattern="embedded-post-wrap")
        
        # Unwrap "youtube-wrap" and "youtube-inner" to leave just the iframe
        clean_body = unwrap_balanced_div(clean_body, class_pattern="youtube-wrap")
        clean_body = unwrap_balanced_div(clean_body, class_pattern="youtube-inner")





        # Construct Markdown
        full_content = f"""+++
title = "{title}"
url = "/posts/letters/{letter_id}"
date = {date}
substack_url = "{substack_url}"
draft = false
+++

<div class="substack-post-content">
<div class="post-header">
{clean_header}
</div>
{clean_body}
</div>
"""
        target_file = os.path.join(output_dir, f"{letter_id}.md")
        with open(target_file, 'w') as f:
            f.write(full_content)
        
        print(f"Generated {target_file}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 process_letter_json.py <scraped_dir>")
        sys.exit(1)
        
    scraped_dir = sys.argv[1]
    output_dir = 'output'
    process_letters(scraped_dir, output_dir)
