import scrapy
from scrapy.spiders.init import InitSpider, Spider
from tutorial.items import CompanyInfo, Review
from bs4 import BeautifulSoup

class GlassDoor(InitSpider):
    name = "glassdoor"
    login_url = 'https://www.glassdoor.co.uk/profile/login_input.htm'

    #https: // www.glassdoor.co.uk / index.htm

    def init_request(self):
        return scrapy.Request(
            url=self.login_url,
            callback=self.login,
        )

    def login(self, response):
        yield scrapy.FormRequest.from_response(
            response=response,
            formid='login_form',
            formdata={
                'userEmail': 'riscott@web.de',
                'userPassword': 'DaDo23$1',
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
        numOfPages = 21549 // 10
        urls = [
            'https://www.glassdoor.co.uk/Reviews/london-reviews-SRCH_IL.0,6_IM1035_IP%s.htm'%i for i in range(5,15)
        ]
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse_main_page)


    def parse_main_page(self, response):
        '''
        parses list of companies, per company starts filling up the CompanyInfo() item 
        and passes on the request to parse the company overview page
        '''
        BaseUrl = "https://www.glassdoor.co.uk/"
        companies = response.css("div.eiHdrModule.module.snug")
        
        for comp in companies:
            item = CompanyInfo()
            item['main_url'] = response.url
            item['companyname'] = comp.css("a.tightAll.h2::text").get().strip(' ')
            item['rating'] = comp.css("span.bigRating.strong.margRtSm.h1::text").get()
            item['rec2friend'] = int(comp.css("span.minor.hideHH.margRtLg.block.margTopXs::text").get().lstrip(' ').split('%')[0]) / 100
            numberOfReviews_str = comp.css("a.eiCell.cell.reviews span.num.h2::text").get().lstrip()
            item['numberOfReviews'] = int(float(numberOfReviews_str.replace('k', 'e3')))
            link2CompanyOverview = BaseUrl + comp.css("a.tightAll.h2::attr(href)").extract()[0]
            item['link2CompanyOverview'] = link2CompanyOverview

            request = scrapy.Request(link2CompanyOverview, callback=self.parse_company_page)
            request.meta['my_meta_item'] = item    ## passing item in the meta dictionary

            yield request


    def parse_company_page(self, response):
        '''
        parses company overview page to get metadata (e.g. size, revenue, founded..)
        link to reviews is sent to callback 'parse_reviews'
        yields the company item with metadata and request to review page
        '''
        item = response.meta['my_meta_item']
        
        # for checking later:
        item['companynameOnCompanyOverview'] = response.css("h1.strong.tightAll::attr(data-company)").get()

        infoBox = response.css("div.info.flexbox.row.col-hh div.infoEntity")

        item['homepage'] = infoBox[0].css("div.infoEntity span.value.website a.link::attr(href)").get()
        rest = response.css("div.info.flexbox.row.col-hh div.infoEntity").css("div.infoEntity span.value::text").getall()

        item['Headquarter'] = rest[0]
        item['Size'] = rest[1]
        item['Founded'] = rest[2]
        item['Type'] = rest[3]
        item['Industry'] = rest[4]
        item['Revenue'] = rest[5]

        item['ceo_approval'] = float(response.xpath('//*[@id="EmpStats_Approve"]').css('div::attr(data-percentage)').get())/100
        item['ceo_ratings'] = response.css('div.minor.numCEORatings::text').get()

        item['activityLevel'] = response.css("a.activityLevel::text").get()

        reviews_url = response.css('div.module.snug.empStatsAndReview a.moreBar::attr(href)').get()
        reviews_url = 'https://www.glassdoor.co.uk' + reviews_url
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
        company = item['companyname']
        current_review_page = response.url

        reviews_html_list = response.css('div.hreview').getall()
        if reviews_html_list:
            for rev_html in reviews_html_list:
                review = self.get_review(rev_html, company, current_review_page)
                yield review

            # follow pagination
            link2follow = response.css("a.pagination__ArrowStyle__nextArrow::attr(href)").get()
            yield response.follow(link2follow, self.parse_reviews, meta = {'my_meta_item':item})
        

    def get_review(self, review_html, company, current_review_page):
        soup = BeautifulSoup(review_html, features="lxml")
        review = Review()

        # company and page link fro debugging
        review['company'] = company
        review['review_url'] = current_review_page

        # summary
        review['summary'] = soup.find('div').find('a').find('span').text
        
        # overall Rating
        review['overallRating'] = soup.find('span',class_="value-title")['title']
        
        # subratings
        classes = soup.find('div', class_="subRatings module stars__StarsStyles__subRatings").find_all('div', class_="minor")
        classes = [clas.text.lower().replace(' ', '_').replace('/', '_').replace('&', '') for clas in classes]
        subratings = soup.find('div', class_="subRatings module stars__StarsStyles__subRatings").find_all('span' , class_="gdBars gdRatings med")
        subratings = [sub['title'] for sub in subratings]
        subratings_dict = {k:v for k,v in zip(classes,subratings)}
        review.update(subratings_dict)

        # employee info 
        review['employee_role'] = soup.find('span', class_= 'authorJobTitle middle reviewer').text
        review['employee_timeWorking'] = soup.find('p', class_= "mainText mb-0").text

        # for non featured reviews get time :
        date = soup.find('time', class_ = 'date subtle small')
        if date is not None:
            review['datetime'] = date['datetime']
        else:
            review['datetime'] = None

        # is featured not not
        if soup.find('div', class_="featuredFlag") is not None:
            review['featured_review'] = True
        else:
            review['featured_review'] = False

        # recommeder bar (the three coloured things)
        recommendBar = soup.find('div', class_="row reviewBodyCell recommends")
        if recommendBar is not None:
            recommendBar_items = recommendBar.find_all('div')
            review.update({k:v for k,v in zip(['recommends', 'outlook', 'approves_ceo'],[rec.find('span').text for rec in recommendBar_items])})
        else: 
            review.update({k:v for k,v in zip(['recommends', 'outlook', 'approves_ceo'],[None,None,None])})

        # the actual review
        pros_cons_adv = soup.find_all('div',class_ = "mt-md")

        keys = [_.find('p' ,class_="strong").text.lower().replace(' ', '_') for _ in pros_cons_adv]

        vals = [_.find_all('p')[1].text for _ in pros_cons_adv]

        review.update({k:v for k,v in zip(keys, vals)})
        
        return review

