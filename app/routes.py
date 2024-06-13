from app import app
from flask import render_template, request, redirect, url_for
import os
import json
from app import utils
import requests
import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
from bs4 import BeautifulSoup

@app.route('/')
def index():
    return render_template('index.html.jinja')

@app.route('/extract', methods=['POST', 'GET'])
def extract():
    if request.method == "POST":
        product_id = request.form.get("product_id")
        url = f"https://www.ceneo.pl/{product_id}"
        response = requests.get(url)
        if response.status_code == requests.codes['ok']:
            page = BeautifulSoup(response.text, "html.parser")
            opinions_count = page.select_one("a.product-review__link > span")
            if opinions_count:
                product_name = utils.get_data(page,"h1")
                url = f"https://www.ceneo.pl/{product_id}#tab=reviews"
                all_opinions = []
                while(url):
                    print(url)
                    response = requests.get(url)
                    page = BeautifulSoup(response.text, "html.parser")
                    opinions = page.select("div.js_product-review")
                    for opinion in opinions:
                        single_opinion = {
                            key: utils.get_data(opinion, *value)
                                for key, value in utils.selectors.items()
                        }
                        all_opinions.append(single_opinion)
                    try:
                        url = "https://ceneo.pl"+page.select_one("a.pagination__next")["href"]
                    except TypeError:
                        url = None
                if not os.path.exists("app/data"):
                    os.mkdir("app/data")
                if not os.path.exists("app/data/opinions"):
                    os.mkdir("app/data/opinions")
                jf = open(f"app/data/opinions/{product_id}.json", "w", encoding="UTF-8")
                json.dump(all_opinions, jf, indent=4, ensure_ascii=False)
                jf.close()
                opinions = pd.DataFrame.from_dict(all_opinions)
                opinions.stars = opinions.stars.apply(lambda s: s.split('/')[0].replace(',', '.')).astype(float)
                stats = {
                    "product_id": product_id,
                    "product_name": product_name,
                    "opinions_count": opinions.shape[0],
                    "pros_count": int(opinions.pros.astype(bool).sum()),
                    "cons_count": int(opinions.cons.astype(bool).sum()),
                    "average_stars": opinions.stars.mean(),
                    "stars_distr": opinions.stars.value_counts().reindex(np.arange(0,5.5,0.5), fill_value=0).to_dict(),
                    "recommendation_distr": opinions.recommendation.value_counts().reindex(["Polecam", "Nie polecam", None], fill_value=0).to_dict(),
                }
                if not os.path.exists("app/data/products"):
                    os.mkdir("app/data/products")
                jf = open(f"app/data/products/{product_id}.json", "w", encoding="UTF-8")
                json.dump(stats, jf, indent=4, ensure_ascii=False)
                jf.close()
                return redirect(url_for('product', product_id=product_id))
            return render_template('extract.html.jinja', error="Produkt o podanym kodzie nie posiada opinii.")
        return render_template('extract.html.jinja', error="Produkt o podanym kodzie nie istnieje.")
    return render_template('extract.html.jinja')

@app.route('/products')
def products():
    products_list = [filename.split(".")[0] for filename in os.listdir('app/data/opinions')]
    products = []
    for product in products_list:
        jf = open(f"app/data/products/{product}.json", "r", encoding="UTF-8")
        products.append(json.load(jf))
        jf.close()
    return render_template('products.html.jinja', products=products)

@app.route('/about')
def about():
    return render_template('about.html.jinja')

@app.route('/product/<product_id>')
def product(product_id):
    if not os.path.exists("app/data/opinions"):
        return redirect(url_for('extract'))
    jf = open(f"app/data/opinions/{product_id}.json", "r", encoding="UTF-8")
    opinions = json.load(jf)
    jf.close()
    return render_template('product.html.jinja', product_id=product_id, opinions=opinions)