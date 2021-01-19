from flask import Flask, request, render_template
import github_extension
import wikidata_extension

app = Flask(__name__)
app.config["DEBUG"] = True

@app.route('/')
def hello_world():
    return render_template('main_page.html')

@app.route('/extension/<path:id>')
def extension(id):
    gm = github_extension.github_metadata(id)

    return render_template('display_extension.html', **gm)

@app.route('/wikidata/<path:id>')
def wd_extension(id):
    wdm = wikidata_extension.wikidata_metadata(id)
    if 'error' in wdm:
        return render_template('error_page.html', **wdm)
    return render_template('display_wikidata.html', **wdm)

@app.route('/wikidata')
def wd_home():
    return render_template('wikidata_main.html')

@app.route('/wd_search')
def wd_search():
    res = wikidata_extension.search(request.args.get('query'))
    return render_template('wikidata_search_results.html', matches=res)
