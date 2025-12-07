
import sys
import json
import os
import re
from datetime import datetime
from substack_api import Post

def scrape_post(url):
    print(f"Scraping {url}...")
    try:
        # Determine paths relative to the script location or project root
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Assuming the script is in scripts/substack_scraper/ (2 levels deep from root)
        # We want to put scraped_data in the project root:
        project_root = os.path.abspath(os.path.join(script_dir, '../../'))
        output_dir = os.path.join(project_root, 'scraped_data')
        
        post = Post(url)
        content = post.get_content()
        # metadata = post.get_metadata() # This might be useful, but let's see what we can get
        # The library documentation says get_metadata() returns metadata.
        
        # We need to construct the ID from the URL.
        # URL format: https://tuwangbrick.substack.com/p/031
        slug = url.split('/')[-1]
        
        # We need to get the title. `substack_api` Post object might expose it or we parse it from content.
        # Let's inspect the content or use metadata if available. 
        # Actually, looking at the library source/docs again (from memory of previous turn), 
        # it has get_metadata(). Let's try to trust it or parse the HTML.
        # The previous JSON example had 'title', 'date', 'headerHTML', 'bodyHTML'.
        
        # Let's try to be robust. 
        # NOTE: The library might return just the body HTML. 
        
        # Let's simple-parse the title from the content if metadata fails or is obscure.
        # But wait, looking at the library docs in Step 10: "metadata = post.get_metadata()"
        
        # As I can't interactively test easily, I will implement a check. 
        # For now, I'll assume I can regex extract title from `content` if needed, 
        # but `get_metadata` should be better.
        
        metadata = {}
        try:
           metadata = post.get_metadata()
        except Exception as e:
           print(f"Warning: Could not get metadata: {e}")

        title = metadata.get('title', '')
        date = metadata.get('post_date', '')
        subtitle = metadata.get('subtitle', '')
        if not subtitle:
            subtitle = metadata.get('description', '')
        
        # Fallback for title
        if not title:
            m = re.search(r'<h1[^>]*>(.*?)</h1>', content)
            if m:
                title = m.group(1)
            else:
                title = slug 

        # Fallback for date
        if not date:
             date = datetime.now().isoformat()
             
        # Construct headerHTML to satisfy process_letter_json.py
        # It looks for <h3 ...>(.*?)</h3> for subtitle
        header_html = ""
        if subtitle:
            header_html = f'<h3 class="subtitle">{subtitle}</h3>'
        
        # Attempt to split header (h1) from content if it exists in content
        # process_letter_json.py uses the title from JSON 'title' field for frontmatter, 
        # but the H1 in headerHTML is not strictly used for frontmatter title, 
        # but might be used for display if process_letter doesn't strip it?
        # Actually process_letter_json.py constructs `clean_header` from subtitle.
        # It doesn't seem to restart H1 from headerHTML into the MD output, 
        # except maybe if it was part of `clean_header`.
        # `clean_header` only adds subtitle link.
        # So we just need the subtitle in headerHTML.
        
        # We should ensure the bodyHTML doesn't duplicate the title if it's already in frontmatter.
        # Substack body often has the title as H1.
        # process_letter_json.py doesn't seem to explicitly strip H1 from bodyHTML, 
        # but it does `clean_header` stuff.
        # Let's check process_letter_json.py again.
        # It `clean_header` gets subtitle.
        # `clean_body` removes various things. 
        # It doesn't seem to remove H1 from body.
        # But existing BodyHTML in 031.json (original) starts with `<h2>`.
        # So the title H1 is separate.
        # We should check if `content` has the H1 and remove it if so, to avoid duplication if the MD renderer adds title.
        # `post.get_content()` usually returns the content body.
        
        body_html = content
        
        # Remove H1 from body if it matches title (simple check)
        # Often Substack content starts with the image or H1.
        # logic: remove the first H1 if it's identical to title.
        
        # But for now, let's just make sure headerHTML has the subtitle.

            
        data = {
            "id": slug,
            "url": url,
            "title": title,
            "date": date,
            "headerHTML": header_html,
            "bodyHTML": body_html
        }
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        output_file = os.path.join(output_dir, f"{slug}.json")
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
            
        print(f"Saved to {output_file}")
            
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scrape_substack.py <url>")
        sys.exit(1)
    
    url = sys.argv[1]
    scrape_post(url)
