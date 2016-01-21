import sys
import os
import datetime
import json

import mock

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.test import TestCase
# import unittest
from django.http import HttpRequest

# if __name__ == '__main__':
#     BASE_DIR = '~/Projects/retirement1.6/retirement/retirement_api'
# else:
#     BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

from retirement_api.views import param_check, income_check, estimator, get_full_retirement_age, claiming
from retirement_api.utils.ss_calculator import get_retire_data

today = datetime.datetime.now().date()

PARAMS = {
    'dobmon': 8,
    'dobday': 14,
    'yob': 1970,
    'earnings': 70000,
    'lastYearEarn': '',  # possible use for unemployed or already retired
    'lastEarn': '',  # possible use for unemployed or already retired
    'retiremonth': '',  # leve blank to get triple calculation -- 62, 67 and 70
    'retireyear': '',  # leve blank to get triple calculation -- 62, 67 and 70
    'dollars': 1,  # benefits to be calculated in current-year dollars
    'prgf': 2
}


class ViewTests(TestCase):
    req_good = HttpRequest()
    req_good.GET['dob'] = '1955-05-05'
    req_good.GET['income'] = '40000'
    req_blank = HttpRequest()
    req_blank.GET['dob'] = ''
    req_blank.GET['income'] = ''
    req_invalid = HttpRequest()
    req_invalid.GET['dob'] = '1-2-%s' % (today.year + 5)
    req_invalid.GET['income'] = 'x'
    return_keys = ['data', 'error']

    @mock.patch('retirement_api.models.Page.objects.get')
    @mock.patch('retirement_api.models.AgeChoice.objects.all')
    @mock.patch('retirement_api.models.Tooltip.objects.all')
    @mock.patch('retirement_api.models.Question.objects.all')
    @mock.patch('retirement_api.models.Step.objects.filter')
    def test_base_view(self,
                       mock_step,
                       mock_question,
                       mock_tooltip,
                       mock_agechoice,
                       mock_page):
        mock_step.return_value = []
        mock_question.return_value = []
        mock_tooltip.return_value = []
        mock_agechoice.return_value = []
        mock_page.return_value = []
        mock_render_to_response = mock.MagicMock()
        mock_request = mock.Mock()
        claiming(mock_request)
        self.assertTrue(mock_step.call_count == 1)
        self.assertTrue(mock_question.call_count == 1)
        self.assertTrue(mock_tooltip.call_count == 1)
        self.assertTrue(mock_agechoice.call_count == 1)
        self.assertTrue(mock_page.call_count == 1)
        claiming(mock_request, es=True)
        self.assertTrue(mock_page.call_count == 2)

    def test_param_check(self):
        self.assertEqual(param_check(self.req_good, 'dob'), '1955-05-05')
        self.assertEqual(param_check(self.req_good, 'income'), '40000')
        self.assertEqual(param_check(self.req_blank, 'dob'), None)
        self.assertEqual(param_check(self.req_blank, 'income'), None)

    def test_income_check(self):
        self.assertEqual(income_check('544.30'), 544)
        self.assertEqual(income_check('$55,000.15'), 55000)
        self.assertEqual(income_check('0'), 0)
        self.assertEqual(income_check('x'), None)
        self.assertEqual(income_check(''), None)

    def test_get_full_retirement_age(self):
        request = self.req_blank
        response = get_full_retirement_age(request, birth_year='1953')
        self.assertTrue(json.loads(response.content) == [66, 0])
        response2 = get_full_retirement_age(request, birth_year=1957)
        self.assertTrue(json.loads(response2.content) == [66, 6])
        response3 = get_full_retirement_age(request, birth_year=1969)
        self.assertTrue(json.loads(response3.content) == [67, 0])
        response4 = get_full_retirement_age(request, birth_year=969)
        self.assertTrue(response4.status_code == 400)

    def test_estimator_url_data(self):
        request = self.req_blank
        response = estimator(request, dob='1955-05-05', income='40000')
        self.assertTrue(type(response.content) == str)
        rdata = json.loads(response.content)
        for each in self.return_keys:
            self.assertTrue(each in rdata.keys())

    def test_estimator_url_data_bad_income(self):
        request = self.req_blank
        response = estimator(request, dob='1955-05-05', income='z')
        self.assertTrue(response.status_code == 400)

    def test_estimator_url_data_bad_dob(self):
        request = self.req_blank
        response = estimator(request, dob='1955-05-xx', income='4000')
        self.assertTrue(response.status_code == 400)

    def test_estimator_query_data(self):
        request = self.req_good
        response = estimator(request)
        self.assertTrue(response.status_code == 200)
        self.assertTrue(type(response.content) == str)
        rdata = json.loads(response.content)
        for each in self.return_keys:
            self.assertTrue(each in rdata.keys())

    def test_estimator_query_data_blank(self):
        request = self.req_blank
        response = estimator(request)
        self.assertTrue(response.status_code == 400)

    def test_estimator_query_data_blank_dob(self):
        request = self.req_blank
        response = estimator(request, income='40000')
        self.assertTrue(response.status_code == 400)

    def test_estimator_query_data_blank_income(self):
        request = self.req_blank
        response = estimator(request, dob='1955-05-05')
        self.assertTrue(response.status_code == 400)

    # def test_estimator_query_data_bad_dob(self):
    #     request = self.req_invalid
    #     response = estimator(request, income='40000')
    #     self.assertTrue(response.status_code == 400)

    # def test_estimator_query_data_bad_dob_of_today(self):
    #     request = self.req_blank
    #     response = estimator(request, income='40000', dob="%s" % today)
    #     self.assertTrue(response.status_code == 400)

    def test_estimator_query_data_bad_income(self):
        request = self.req_invalid
        response = estimator(request, dob='1955-05-05')
        self.assertTrue(response.status_code == 400)
