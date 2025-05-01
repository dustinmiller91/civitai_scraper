# civitai_scraper
For scraping images and prompt/tag metadata from civitai

Civitai's API is basically useless since it doesn't allow for downloading of actual images or any prompt/tag data (you know...the good stuff).To get around this limitation I wrote this basic scraper to read from a list of image urls in a .txt file and download that information.

Currently it's just set up to download just the positive prompt and the auto-generated tags into a single text file, but you can easily modify it to grab whatever you want including negatives, model/lora info/etc.

Worth noting that civitai uses a lot of javascript rendering, so you can't just scrape the HTML with beautifulsoup. Instead you have to use selenium and the browser of your choice (firefox in this implementation) to load the web page and fully render the javascript before exporting the page source to beautifulsoup for parsing. Feel free to for this repo. I don't care if you credit me or not.
