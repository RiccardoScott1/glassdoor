# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class CompanyInfo(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    main_url = scrapy.Field()
    company_name = scrapy.Field()
    company_rating = scrapy.Field()
    rec2friend = scrapy.Field()
    number_of_reviews = scrapy.Field()
    link_company_overview =  scrapy.Field()

    company_name_on_company_overview = scrapy.Field()
    homepage = scrapy.Field()
    headquarters = scrapy.Field()
    size = scrapy.Field()
    founded = scrapy.Field()
    type = scrapy.Field()
    industry = scrapy.Field()
    revenue = scrapy.Field()
    ceo_approval = scrapy.Field()
    ceo_ratings = scrapy.Field()
    activity_level = scrapy.Field()
    reviews_url = scrapy.Field()
    ceo_img_link = scrapy.Field()
    ceo_name = scrapy.Field()
    part_of = scrapy.Field()
    competitors = scrapy.Field()


class Review(scrapy.Item):
    review_url = scrapy.Field() 
    company = scrapy.Field() 
    title = scrapy.Field()
    overall_rating = scrapy.Field()
    work_life_balance = scrapy.Field()
    culture_values = scrapy.Field()
    career_opportunities = scrapy.Field()
    compensation_and_benefits = scrapy.Field()
    senior_management = scrapy.Field()
    employee_role = scrapy.Field()
    employee_location = scrapy.Field()
    employee_time_working = scrapy.Field()
    review_date = scrapy.Field()
    featured_review = scrapy.Field()
    recommend_bar = scrapy.Field()

    pros = scrapy.Field()
    cons = scrapy.Field()
    advice_to_management = scrapy.Field()
