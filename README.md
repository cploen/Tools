This repo contains some tools to speed things up:

1. jcache-bulk-get.sh:
	 lets you list the run numbers as arguments (space, no comma) and automate the jcache get request.  It's hardwired to pin the file for 14 days.
2. data_search.py:
	Initially, I used to loop over a folder containing all the metadata from runs and yank the sparsification status from one of the vme files.  I put the results in individual csv lists named by their configuration. Open to ideas/expansion!

3. logbook/webscraper.py:
	We needed a way to get the autologged metadata from the logbook website.  This sends a login and search payload to logsbook.jlab.org and downloads attached files.
	
	type $python webscraper.py -h for available flags
	
	Search hierarchy:
	- json file contains search payload and output folder name.  Edit this and you can just run the script and go.
	- command line search terms: Overrides json file, let's you play around with your parameters without having to open/edit/save the json.
	- --filtering flag: this provides the strict search unavailable (as far as I can tell) from the logbook site.  It will match only the exact search string.  At least, that's the idea - I'm still testing it.
So, 
--filtering: most strict
- command line search terms: overrides json file
- settings.json: holds the search payload - edit here, not in the script.

Default behavior:
- settings set for Hall C logbook, NPS run period.  I don't have a list of the codes for the other logbooks, but you can use the developer tools on the website to figure it out and then just edit settings.json.

4. elog-scraper/elog.py
        We needed an organized  way to archive the elogs for our experiments.  This script authenticates securely and uses BeautifulSoup to parse the html.  It handles pagination cleanly and only downloads new entries.  The entries are saved to folders named by metadata and a subject slug, and the attachments, text, and metadata are downloaded and organized cleanly. See the readme in the folder for more instruction.  

		However, you must use this on a JLab computer, like ifarm.  I can't satisfy the Cloudfare security challenge programmatically.
