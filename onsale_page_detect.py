# -*- coding: utf-8 -*-
import sys
import time
import Queue
import threading
import random
import database.mongo_operation
from bs4 import BeautifulSoup
from selenium import webdriver
from driverhandler import DriverHandler
from keywords import curl_keywords,page_keywords,malicous_keywords

reload(sys)
sys.setdefaultencoding('utf-8')

domain_to_get = Queue.Queue()
mongo_conn = database.mongo_operation.MongoConn("10.245.146.37","domain_relation")


class Domain_For_Sale(DriverHandler):

	def __init__(self,timeout=30):

		DriverHandler.__init__(self,'chrome',max_time=timeout)
		self.raw = ""

	def spider(self,domain):
		"""
			模拟浏览器打开网页，进行关键词匹配
		"""

		self.domain = domain
		flag = self.open_web(domain)
		result = 0
		if flag:
			try:
				#若该页面含有<frame>，进入frame中src页面进行匹配
				soup = BeautifulSoup(self.driver.page_source,"lxml")
				frame_url = soup.find("frame")
				if frame_url:
					self.open_web(frame_url['src'])
				result = self.match_keywords()
				self.destory_driver()
			except Exception, e:
				print "Error:", str(e)
		else:
			self.destory_driver()

		return result


	def match_keywords(self):
		"""
		1.先根据跳转后的最终URL，判断URL的特征是否疑似域名售卖URL，匹配成功返回True，不成功则向下继续流程
		2.再根据页面关键词匹配，判断是否为非法域名，若匹配成功返回False，不成功则向下继续流程
		  为减少误判，故需要出现多个非法关键词，才认为该页面非售卖页面
		3.再根据页面关键词匹配，判断是否为售卖页面，匹配成功返回True，否则False
		"""

		curl = self.driver.current_url.lower()
		page = self.driver.page_source.lower()
		title = self.driver.title
		td_count = page.count("<td")
		#td_count 记录页面有多少表单元素，若过多则为域名售卖网站嫌疑很大

		for keyword in curl_keywords:
			if keyword in curl:
				print "初始URL为 ",self.domain	
				print "重定向后URL为 ",curl
				print "此页面为域名售卖页面，重定向后URL中，关键词为"+keyword
				return True

		#为减少误判，故需要出现多个非法关键词，才认为该页面非售卖页面
		malicous_count = 0
		malicous_kwd = []
		for keyword in malicous_keywords:
			if keyword in page:
				malicous_count += 1
				malicous_kwd.append(keyword)
				if malicous_count > 10 and td_count < 100:
					print "初始URL为 ",self.domain
					print "重定向后URL为 ",curl
					print "此页面为赌博/色情等非法页面,关键词为:\n"+str(malicous_kwd)
					return False

		for keyword in page_keywords:
			if keyword in page:
				print "初始URL为 ",self.domain
				print "重定向后URL为 ",curl
				print "此页面为域名售卖页面,关键词为"+keyword
				return True

		print "初始URL为 ",self.domain
		print "重定向后URL为 ",curl
		print "无法判定此页面属性"
		return False


def get_domain_queue():
	"""
	向待探测队列中加入域名，来源为MONGO数据库
	"""
	collection_name = "ip_relation"
	fetch_domain = mongo_conn.mongo_read(collection_name,{'ip':'23.234.4.153'},{'domains':1,'_id':0},1)
	for cname in fetch_domain:
		random.shuffle(cname['domains'])
		for domain in cname['domains']:
			domain_to_get.put(domain)
	domain_to_get.put("zuanshimi.com")
	domain_to_get.put("6848669.com/")
	domain_to_get.put("818023.com")
	print domain_to_get.qsize()



def match_all():
	while domain_to_get.qsize()>0:
		d = Domain_For_Sale()
		domain = domain_to_get.get()
		#print "待检测URL http://"+str(domain)
		result = d.spider("http://"+str(domain))
		del d
		print domain_to_get.qsize()
		if domain_to_get.qsize() == 0:
			sys.exit()


def single_test():

	domain_to_get.put("zuanshimi.com")
	domain_to_get.put("6848669.com/")
	domain_to_get.put("818023.com")
	match_all()


def main():

	#线程总数量
    thread_num = 5
    get_domain_queue()
    thread_list = list();
    # 先创建线程对象
    for i in range(0, thread_num):
        thread_name = "thread_%s" %i
        thread_list.append(threading.Thread(target = match_all, name = thread_name))
 
    # 启动所有线程
    for thread in thread_list:
        thread.start()
 
    # 主线程中等待所有子线程退出
    for thread in thread_list:
        thread.join(timeout=5)

    print "ENDS"


if __name__ == '__main__':
	'''
	测试模式： python domain_onsale_detect.py test
	可在settings.py中关闭HEADLESS模式，开启图片渲染

	多线程探测模式： python domain_onsale_detect.py
	可在main()函数中修改线程数量，get_domain_queue()中设置待探测域名队列数据来源
	'''
	if len(sys.argv)>1:
		if sys.argv[1] == 'test':
			single_test()
	else:
		main()

