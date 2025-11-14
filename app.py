import os
import sys
import json
import math
import time
import re
from datetime import datetime, timezone
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

import pytz
import requests
from requests.exceptions import Timeout, RequestException
from flask import Flask, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")

MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")
MISTRAL_MODEL = os.environ.get("MISTRAL_MODEL", "mistral-large-latest")
TOKEN_LIMIT_PER_DAY = int(os.environ.get("DAILY_TOKEN_LIMIT", "100000"))
USAGE_FILE = os.path.join(os.path.dirname(__file__), "usage.json")

HEADERS_REDDIT = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}


def _load_usage():
    if not os.path.exists(USAGE_FILE):
        return {"date": _utc_date_str(), "tokens": 0}
    try:
        with open(USAGE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Reset if date changed (UTC midnight)
        if data.get("date") != _utc_date_str():
            return {"date": _utc_date_str(), "tokens": 0}
        return data
    except Exception:
        return {"date": _utc_date_str(), "tokens": 0}


def _save_usage(data):
    try:
        with open(USAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


def _utc_date_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _estimate_tokens(text: str) -> int:
    # Rough estimate: 1 token ~ 4 chars
    return max(1, math.ceil(len(text) / 4))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search", methods=["POST"]) 
def search():
    subreddit = request.form.get("subreddit", "").strip()
    keyword = request.form.get("keyword", "").strip()
    if not subreddit or not keyword:
        flash("Please enter subreddit and keyword")
        return redirect(url_for("index"))

    # Use RSS feed instead of JSON API to avoid 403 errors
    # Filter to posts within 1 year
    query = {
        "q": keyword,
        "restrict_sr": "on",  # Restrict search to this subreddit only
        "sort": "top",
        "t": "year",  # Only posts from the last year
        "limit": 100  # RSS returns more, we'll filter to top 10
    }
    url = f"https://www.reddit.com/r/{subreddit}/search.rss?{urlencode(query)}"

    try:
        print(f"[Reddit RSS] Requesting: {url}", file=sys.stderr, flush=True)
        resp = requests.get(url, headers=HEADERS_REDDIT, timeout=15)
        print(f"[Reddit RSS] Status: {resp.status_code}", file=sys.stderr, flush=True)
        if resp.status_code != 200:
            print(f"[Reddit RSS] Response: {resp.text[:500]}", file=sys.stderr, flush=True)
            flash(f"Reddit API Error: {resp.status_code} - Check terminal for details")
            return redirect(url_for("index"))
        
        # Parse RSS XML
        root = ET.fromstring(resp.content)
        posts = []
        
        # RSS namespace
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        for entry in root.findall('.//atom:entry', ns):
            title_elem = entry.find('atom:title', ns)
            link_elem = entry.find('atom:link', ns)
            author_elem = entry.find('atom:author/atom:name', ns)
            updated_elem = entry.find('atom:updated', ns)
            content_elem = entry.find('atom:content', ns)
            
            
            if title_elem is None or link_elem is None:
                continue
                
            title = title_elem.text
            link = link_elem.get('href', '')
            author = author_elem.text if author_elem is not None else 'unknown'
            
            # Extract permalink from link
            permalink_match = re.search(r'(https://www\.reddit\.com)?(/r/[^/]+/comments/[^/]+/[^/]+/?)(?:\?|$)', link)
            permalink = permalink_match.group(2) if permalink_match else ''
            
            # Verify post is from the target subreddit
            if permalink and f'/r/{subreddit.lower()}/' not in permalink.lower():
                print(f"[Reddit RSS] Skipping post from different subreddit: {permalink}", file=sys.stderr, flush=True)
                continue
            
            # RSS doesn't include score/comments, will fetch from JSON API
            score = 0
            num_comments = 0
            
            # Extract post ID from permalink
            post_id_match = re.search(r'/comments/([a-z0-9]+)/', permalink)
            post_id = post_id_match.group(1) if post_id_match else ''
            
            posts.append({
                "id": post_id,
                "title": title,
                "score": score,
                "author": author,
                "num_comments": num_comments,
                "created_utc": 0,  # Not available in RSS
                "permalink": permalink,
                "selftext": "",  # Will fetch when viewing post
                "url": link,
                "subreddit": subreddit,
            })
        
        # Limit to 15 posts to avoid rate limiting when fetching scores
        posts = posts[:15]
        print(f"[Reddit RSS] Found {len(posts)} posts from RSS, fetching scores...", file=sys.stderr, flush=True)
        
        # Fetch real scores and comments from JSON API for each post
        for i, post in enumerate(posts):
            if not post['permalink']:
                continue
            try:
                json_url = f"https://www.reddit.com{post['permalink']}.json"
                json_resp = requests.get(json_url, headers=HEADERS_REDDIT, timeout=10)
                if json_resp.status_code == 200:
                    json_data = json_resp.json()
                    if json_data and len(json_data) > 0:
                        post_data = json_data[0]['data']['children'][0]['data']
                        post['score'] = post_data.get('score', 0)
                        post['num_comments'] = post_data.get('num_comments', 0)
                        print(f"[Reddit RSS] Post {post['id']}: {post['score']} upvotes, {post['num_comments']} comments", file=sys.stderr, flush=True)
                elif json_resp.status_code == 429:
                    print(f"[Reddit RSS] Rate limited at post {i+1}, using remaining posts", file=sys.stderr, flush=True)
                    break  # Stop fetching if rate limited
                else:
                    print(f"[Reddit RSS] Failed to fetch JSON for {post['id']}: {json_resp.status_code}", file=sys.stderr, flush=True)
                
                # Add delay between requests to avoid rate limiting (2 seconds)
                if i < len(posts) - 1:
                    time.sleep(2)
                    
            except Exception as e:
                print(f"[Reddit RSS] Error fetching score for {post['id']}: {e}", file=sys.stderr, flush=True)
                continue
        
        # Sort by score and limit to top 10
        posts.sort(key=lambda x: x.get("score", 0), reverse=True)
        posts = posts[:10]
        
        print(f"[Reddit RSS] Returning top {len(posts)} posts", file=sys.stderr, flush=True)
        return render_template("results.html", posts=posts, subreddit=subreddit, keyword=keyword)
    except ET.ParseError as e:
        print(f"[Reddit RSS] XML Parse Error: {e}", file=sys.stderr, flush=True)
        flash(f"Failed to parse Reddit RSS feed: {e}")
        return redirect(url_for("index"))
    except Exception as e:
        print(f"[Reddit RSS] Error: {e}", file=sys.stderr, flush=True)
        flash(f"Search failed: {e}")
        return redirect(url_for("index"))


@app.route("/post")
def post_detail():
    permalink = request.args.get("permalink", "")
    if not permalink:
        flash("Post link not found")
        return redirect(url_for("index"))

    url = f"https://old.reddit.com{permalink}.json"
    try:
        resp = requests.get(url, headers=HEADERS_REDDIT, timeout=15)
        if resp.status_code != 200:
            flash(f"Failed to fetch post: {resp.status_code}")
            return redirect(url_for("index"))
        arr = resp.json()
        post_data = arr[0]["data"]["children"][0]["data"] if arr and arr[0]["data"]["children"] else {}
        title = post_data.get("title", "")
        selftext = post_data.get("selftext", "")
        subreddit = post_data.get("subreddit", "")
        return render_template("post.html", title=title, selftext=selftext, permalink=permalink, subreddit=subreddit)
    except Exception as e:
        flash(f"Failed to load post: {e}")
        return redirect(url_for("index"))


@app.route("/generate", methods=["POST"]) 
def generate_plan():
    if not MISTRAL_API_KEY:
        flash("Server has not configured Mistral API Key")
        return redirect(url_for("index"))

    title = request.form.get("title", "")
    content = request.form.get("content", "")
    permalink = request.form.get("permalink", "")
    subreddit = request.form.get("subreddit", "")

    usage = _load_usage()
    # Estimate prompt tokens before request
    prompt = build_prompt(title, content, permalink, subreddit)
    est_prompt_tokens = _estimate_tokens(prompt)
    # Keep a conservative headroom for response
    est_response_tokens = 1500
    if usage["tokens"] + est_prompt_tokens + est_response_tokens > TOKEN_LIMIT_PER_DAY:
        flash("Daily AI token limit reached. Quota resets at UTC midnight. Please come back tomorrow.")
        return redirect(url_for("post_detail", permalink=permalink))

    try:
        plan_md, used_tokens = call_mistral(prompt)
        # Update token usage (prompt + estimated response)
        usage["tokens"] += est_prompt_tokens + used_tokens
        _save_usage(usage)
        return render_template("plan.html", plan_md=plan_md, title=title)
    except Exception as e:
        flash(f"Failed to generate execution plan: {e}")
        return redirect(url_for("post_detail", permalink=permalink))


def build_prompt(title: str, content: str, permalink: str, subreddit: str) -> str:
    instr = (
        "You are a senior startup coach. Based on the pain points in the Reddit post below, output an execution plan strictly following this Markdown format:\n\n"
        "# Pain Point Description\n"
        "- Summarize the key pain point in 1-2 sentences.\n\n"
        "# Target Users\n"
        "- Who they are, what scenario they're in, and how they're affected by the pain point.\n\n"
        "# Validation Experiments (3)\n"
        "- For each experiment: goal, hypothesis, execution steps, success criteria, required resources/time cost.\n\n"
        "# 10-Step Checklist\n"
        "- List 10 actionable small steps, as specific as possible.\n\n"
        "Requirements:\n- Output only Markdown, no explanations.\n- Use English.\n- Assume you only have minimal resources.\n"
    )
    src = f"Reddit Post: [{title}](https://www.reddit.com{permalink})\nSubreddit: r/{subreddit}\n\nContent:\n\n{content}\n"
    return instr + "\n---\n\n" + src


def call_mistral(prompt: str):
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }
    body = {
        "model": MISTRAL_MODEL,
        "messages": [
            {"role": "system", "content": "You are a rigorous startup coach. Output only Markdown."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 2048
    }
    
    # Retry logic with exponential backoff
    max_retries = 3
    base_timeout = 120  # Increased from 60 to 120 seconds
    
    for attempt in range(max_retries):
        try:
            timeout = base_timeout + (attempt * 30)  # Increase timeout on retries
            print(f"[Mistral API] Attempt {attempt + 1}/{max_retries}, timeout={timeout}s")
            
            resp = requests.post(url, headers=headers, json=body, timeout=timeout)
            
            if resp.status_code != 200:
                error_msg = f"HTTP {resp.status_code}"
                try:
                    error_detail = resp.json().get("message", resp.text[:200])
                    error_msg += f": {error_detail}"
                except:
                    error_msg += f": {resp.text[:200]}"
                raise RuntimeError(f"Mistral API Error: {error_msg}")
            
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            used_tokens = _estimate_tokens(content)
            print(f"[Mistral API] Success! Generated {used_tokens} tokens")
            return content, used_tokens
            
        except Timeout as e:
            print(f"[Mistral API] Timeout on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                print(f"[Mistral API] Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise RuntimeError(
                    f"Mistral API Timeout: Request timed out after {timeout} seconds. "
                    "Possible causes: 1) Network connection issues 2) API service busy 3) Request content too long. "
                    "Please try again later or check your network connection."
                )
        
        except RequestException as e:
            print(f"[Mistral API] Request error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"[Mistral API] Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise RuntimeError(f"Mistral API Network Error: {str(e)}")
        
        except Exception as e:
            print(f"[Mistral API] Unexpected error: {e}")
            raise RuntimeError(f"Mistral API Unknown Error: {str(e)}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
