import scrapy
from scrapy.spiders.init import InitSpider, Spider
from glassdoor_scraper.items import CompanyInfo, Review
from bs4 import BeautifulSoup
import json

from urllib.parse import urljoin
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

import platform

class GlassDoor(InitSpider):
    # logs into glassdoor
    name = "glassdoor"
    login_url = 'https://www.glassdoor.co.uk/profile/login_input.htm'

    def __init__(self):
        secs = json.load(open('glassdoor_scraper/secrets.json', 'r'))
        self.glassdoor_user = secs['glassdoor_user']
        self.glassdoor_pw = secs['glassdoor_pw']
        self.base_url = "https://www.glassdoor.co.uk/"

        # for selenium
        PLATFORM = platform.system()
        if PLATFORM == 'Darwin':
            self.CHROMEDRIVER_PATH = './glassdoor_scraper/spiders/chromedriver'
        else:
            self.CHROMEDRIVER_PATH = './glassdoor_scraper/spiders/chromedriver_linux'

        WINDOW_SIZE = "1920,1080"
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=%s" % WINDOW_SIZE)
        self.chrome_options = chrome_options

    #https: // www.glassdoor.co.uk / index.htm

    def init_request(self):
        return scrapy.Request(url=self.login_url,
                              callback=self.login,
                              )

    def login(self, response):
        yield scrapy.FormRequest.from_response(
            response=response,
            formid='login_form',
            formdata={
                'userEmail': self.glassdoor_user,
                'userPassword': self.glassdoor_pw,
            },
            callback=self.after_login,
        )

    def after_login(self, response):
        # check login succeed before going on
        if "authentication failed" in response.body:
            self.log("\n\n\nLogin failed\n\n\n", level=log.ERROR)
            return
        # We've successfully authenticated, let's have some fun!
        elif "Sign Out" in response.body:
            self.log("\n\n\nSuccessfully logged in. Let's start crawling!\n\n\n")
        # Now the crawling can begin..
            return self.initialized()


    def start_requests(self):
        # start from the pages listing companies
        number_of_companies = 28874
        number_of_pages = number_of_companies // 10
        urls = [f'https://www.glassdoor.co.uk/Reviews/london-reviews-SRCH_IL.0,6_IM1035_IP{i}.htm'
                for i in range(1,15)]

        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse_main_page)



    def parse_main_page(self, response):
        '''
        parses list of companies, per company starts filling up the CompanyInfo() item 
        and passes on the request to parse the company overview page
        '''

        companies = response.css("div.single-company-result.module ")
        
        for comp in companies:
            item = CompanyInfo()

            item['main_url'] = response.url

            company_name_link_rev = comp.css("div.col-9.pr-0")[0]
            if not company_name_link_rev:
                continue
            item['company_name'] = company_name_link_rev.css('h2 a::text').get()


            link_company_overview = urljoin(self.base_url, company_name_link_rev.css("h2 a::attr(href)").get())
            item['link_company_overview'] = link_company_overview

            item['company_rating'] = company_name_link_rev.css("span.bigRating.strong.margRtSm.h2::text").get()
            item['homepage'] = company_name_link_rev.css("span.url a::attr(href)").get()

            number_of_reviews = comp.css("a.eiCell.cell.reviews.d-inline-block.py-sm span.num.h2::text").get()\
                .strip()\
                .lower()\
                .replace('k', 'e3')

            item['number_of_reviews'] = float(number_of_reviews)


            request = scrapy.Request(link_company_overview, callback=self.parse_company_page)
            request.meta['my_meta_item'] = item    ## passing item in the meta dictionary

            yield request


    def parse_company_page(self, response):
        '''
        parses company overview page to get metadata (e.g. size, revenue, founded..)
        link to reviews is sent to callback 'parse_reviews'
        yields the company item with metadata and request to review page
        '''
        item = response.meta['my_meta_item']

        item['activity_level'] = response.css("a.activityLevel::text").get()

        # for checking later:
        item['company_name_on_company_overview'] = response.css("h1.strong.tightAll::attr(data-company)").get()

        # all the basic info (hq, number of emps, rev. homepage etc)
        info_box = response.css("div.module.empBasicInfo")

        item['homepage'] = info_box[0].css("div.infoEntity span.value.website a.link::attr(href)").get()

        rest_labels = info_box.css("div.infoEntity label::text").getall()
        rest_labels = [i.lower().strip().replace(' ', '_') for i in rest_labels]

        rest_values = info_box.css("div.infoEntity span ::text").getall()
        rest_dict = {k: v for k, v in dict(zip(rest_labels, rest_values)).items() if k in CompanyInfo.fields.keys()}
        item.update(rest_dict)


        # load recommend, ceo approval and image  donuts
        # donuts not available in static html, needs selenium to load scripts
        inner_html = self._get_inner_html(response.url)
        soup = BeautifulSoup(inner_html, features='lxml')

        recommend = soup.find(id='EmpStats_Recommend')
        if recommend:
            recommend = recommend.get('data-percentage', None)
            item['rec2friend'] = recommend

        ceo_appr = soup.find(id='EmpStats_Approve')
        if ceo_appr:
            ceo_appr = ceo_appr.get('data-percentage', None)
            item['ceo_approval'] = ceo_appr

        ceo_ratings = soup.find('div', 'numCEORatings')
        if ceo_ratings:
            ceo_ratings = ceo_ratings.text
            item['ceo_ratings'] = ceo_ratings

        ceo_img_link = soup.find('img', class_='headshot photo lazy lazy-loaded')
        if ceo_img_link:
            ceo_img_link = ceo_img_link.get('src', None)
            item['ceo_img_link'] = ceo_img_link

        ceo_name = soup.find('img', class_='headshot photo lazy lazy-loaded')
        if ceo_name:
            ceo_name = ceo_name.get('title', None)
            item['ceo_name'] = ceo_name


        # link to reviews / send request to reviews
        reviews_url = response.css('a.eiCell.cell.reviews::attr(href)').get()
        reviews_url = urljoin(self.base_url, reviews_url)
        item['reviews_url'] = reviews_url

        request = scrapy.Request(reviews_url, callback=self.parse_reviews)
        request.meta['my_meta_item'] = item

        yield item
        yield request   


    def parse_reviews(self, response):
        '''
        goes through review page:
        yields reviews and follows next page (link2follow) to queue 
        '''
        item = response.meta['my_meta_item']
        company = item['company_name']
        current_review_page = response.url

        reviews_list = response.css('div.gdReview')
        if reviews_list:
            for rev in reviews_list:
                review = self.get_review(rev, company, current_review_page)
                yield review

            # follow pagination and keep the company item in the meta data
            link2follow = response.css("a.pagination__ArrowStyle__nextArrow::attr(href)").get()
            yield response.follow(link2follow, self.parse_reviews, meta = {'my_meta_item':item})
        

    def get_review(self, rev, company, current_review_page):
        soup = BeautifulSoup(rev.get(), features="lxml")
        review = Review()

        # company and page link for debugging
        review['company'] = company
        review['review_url'] = current_review_page
        review['title'] = soup.find('div').find('a').text.strip('"')
        # overall Rating
        review['overall_rating'] = soup.find('div', class_="v2__EIReviewsRatingsStylesV2__ratingNum v2__EIReviewsRatingsStylesV2__small").text

        # subratings
        def get_sub_rating(s):
            return s.find('span', class_='gdStars gdRatings common__StarStyles__gdStars')\
                .find('span', class_='rating')\
                .find('span')['title']


        if (sub_ratings_block := soup.find('ul', class_='undecorated')) is not None:
            sub_ratings = {s.find('div', class_="minor"): get_sub_rating(s) for s in sub_ratings_block}
            sub_ratings = {k.text: v for k, v in sub_ratings.items() if k}

            # rename the keys to field names
            sub_ratings_labels_to_field_names = {'Work/Life Balance':'work_life_balance',
                                             'Culture & Values':'culture_values',
                                             'Career Opportunities':'career_opportunities',
                                             'Compensation and Benefits':'compensation_and_benefits',
                                             'Senior Management':'senior_management'}

            sub_ratings = {sub_ratings_labels_to_field_names[k]:v for k,v in sub_ratings.items()}

            review.update(sub_ratings)

        # employee info
        if (employee_role := soup.find('span', class_= 'authorJobTitle middle')) is not None:
            review['employee_role'] = employee_role.text
        if (employee_location := soup.find('span', class_='authorLocation')) is not None:
            review['employee_location'] = employee_location.text
        if (employee_time_working:= soup.find('p', class_= "mainText mb-0")) is not None :
            review['employee_time_working'] = employee_time_working.text

        # for non featured reviews get time :
        if (date := soup.find('time', class_ = 'date subtle small')) is not None:
            review['review_date'] = date['datetime']

        # is featured not not
        if soup.find('div', class_="featuredFlag") is not None:
            review['featured_review'] = True
        else:
            review['featured_review'] = False

        # recommeder bar (the three coloured things)
        recommendBar = soup.find('div', class_="row reviewBodyCell recommends")
        if recommendBar:
            recommendBar_items = recommendBar.find_all('span')
            review['recommend_bar'] = [el.text for el in recommendBar_items]

        # the actual review text pros and cons
        pro_con_head = "p.strong.mb-0.mt-xsm::text"
        pro_con_text = "p.mt-0.mb-xsm.v2__EIReviewDetailsV2__bodyColor.v2__EIReviewDetailsV2__lineHeightLarge span::text"
        pros_cons = {proscons.css(pro_con_head).get(): proscons.css(pro_con_text).get() for proscons in
                     rev.css("div.v2__EIReviewDetailsV2__fullWidth")}
        pros_cons = {k.lower(): v for k, v in pros_cons.items() if k}

        review.update(pros_cons)
        return review


    def _get_inner_html(self, url):
        browser = webdriver.Chrome(self.CHROMEDRIVER_PATH,
                                   chrome_options=self.chrome_options)
        browser.get(url)
        # some time to render .js
        time.sleep(1)
        # returns the inner HTML as a string
        innerHTML = browser.execute_script("return document.body.innerHTML")
        return innerHTML





