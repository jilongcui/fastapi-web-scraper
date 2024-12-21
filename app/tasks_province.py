# tasks.py

import aiohttp
import asyncio
import time
import random
import os
import base64
import logging
import sys
from bs4 import BeautifulSoup
from urllib.parse import unquote
from app.logs import get_logger
from fastapi import FastAPI, HTTPException, Depends
from models.user import User  # 从models导入用户模型
from app.database import get_interview_collection  # 从app导入数据库函数

# 获取一个特定的 logger 实例
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# StreamHandler für die Konsole
stream_handler = logging.StreamHandler(sys.stdout)
log_formatter = logging.Formatter("%(asctime)s [%(processName)s: %(process)d] [%(threadName)s: %(thread)d] [%(levelname)s] %(name)s: %(message)s")
stream_handler.setFormatter(log_formatter)
logger.addHandler(stream_handler)

file_handler = logging.FileHandler('app.log')
file_handler.setFormatter(log_formatter)
logger.addHandler(file_handler)

async def fetch_captcha_svg(url, headers):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                svg_data = await response.text()
                # logger.info(f"Fetched SVG: {svg_data}")  # 打印前100个字符以示例
                return svg_data
            else:
                logger.info(f"Failed to fetch SVG, status code: {response.status}")
                return None
            
# def image2Code2(imageUrl):
#     api_endpoint =f"https://mianshi.xiaohe.biz/api/interview-set/svg2Answer"
#     headers = {
#         # 'Authencation': f'{authToken}',
#         'Content-Type': 'application/json'
#     }
#     response = requests.post(api_endpoint, json={"imageUrl": imageUrl},headers=headers)
#     answer = None;
#     code = None
#     if (response.status_code == 200 or response.status_code == 201):
#         code = response.json().get("code", {})
#         if code == 200:
#             data = response.json().get("data", {})
#             answer = data.get("answer")

#     return data

async def image2Code(imageUrl):
    api_endpoint = "https://mian.xiaohe.biz/api/interview-set/svg2Answer"
    headers = {
        # 'Authentication': f'{authToken}',  # 确保替换为你的真实认证令牌
        'Content-Type': 'application/json'
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(api_endpoint, json={"imageUrl": imageUrl}, headers=headers) as response:
            data = {}
            if response.status in (200, 201):
                # 如果返回状态码是200或201，处理响应内容
                logger.info("Request successful")
                data = await response.json()  # 假设服务器返回JSON格式数据
                code = data.get("code", {})
                if code == 200:
                    data = data.get("data", {})
                else:
                    logger.info(f"Request failed with status code: {response.status}")
            return data
# 定义API端点和图像URL

imageUrl = "your_image_url_here"


async def getUrls(paperId:str) -> dict:
    # 抓取svgStr
    url = "https://www.gkzenti.cn/captcha/math"
    timestamp = int(time.time())
    headers = {
        'Accept': "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        'Cookie': "connect.sid=s%3AFIZCYvlp4vhfk4l5eEq9rr74JCd2an67.uP2a3PFUS8LNC6LVfVaEu2XoG27NIIymPDducAD%2BM48; Hm_lvt_db5c56a1da081947699f2e5bece459c7=1732881600; HMACCOUNT=1A150266D1AAAB30; cls=%E5%85%AC%E5%8A%A1%E5%91%98%E9%9D%A2%E8%AF%95; province=%E5%9B%BD%E8%80%83; Hm_lpvt_db5c56a1da081947699f2e5bece459c7=1734586863",
        "Cookie": f"connect.sid=s%3AasmGihKKO8OTgnFL2y_LgZmYVtts86x6.bbnOMAmmxvMpdGk7ctgHBdB7W4CTwE47z0Ku0x9e9xA; Hm_lvt_db5c56a1da081947699f2e5bece459c7=1734590397; HMACCOUNT=96C839E210B265AA; province=%E5%9B%BD%E8%80%83; cls=%E5%85%AC%E5%8A%A1%E5%91%98%E9%9D%A2%E8%AF%95; Hm_lpvt_db5c56a1da081947699f2e5bece459c7={timestamp}",
        "User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 QuarkPC/1.10.0.169"
    }
    headers['Referer'] = f"https://www.gkzenti.cn/paper/{paperId}"
    svgStr = await fetch_captcha_svg(url, headers)
    # 将转义字符移除
    svg_string = svgStr.replace('\"', '"')

    # 将修正后的SVG字符串编码为UTF-8字节
    svg_bytes = svg_string.encode('utf-8')
    
    # 对字节进行Base64编码
    base64_encoded_svg = base64.b64encode(svg_bytes).decode('utf-8')

    # 创建Data URI格式
    data_uri = f'data:image/svg+xml;charset=utf-8;base64,{base64_encoded_svg}'
    
    # 假设image2Answer是在其他地方定义的函数，用于处理encoded data和authentication token。
    data = await image2Code(data_uri)
    code = data.get("answer")
    code = int(code)
    questionUrl = f"https://www.gkzenti.cn/paper/{paperId}"
    explanUrl = f"https://www.gkzenti.cn/explain/{paperId}?mathcode={code}"
    return questionUrl, explanUrl

import re
def getTitleInfo(title):
    # 定义正则表达式模式，忽略月份
    pattern = r'(?P<year>\d{4})年(?:\d{1,2})月\d{1,2}日(?P<department>.*?)面试'

    # 解析每个主题
    title = title.strip().replace("上午", "").replace("下午", "")
    match = re.search(pattern, title)
    if match:
        year = match.group('year')
        department = match.group('department')
        
        logger.info(f"主题: {title}")
        logger.info(f"  年份: {year}")
        logger.info(f"  单位: {department}\n")
        return year, department
    return None, None

async def replace_image_urls(markdown_text, authToken=""):
    # 定义正则表达式来匹配 !img[](url)
    # pattern = r'!\[\]\(([^)]+)\)'
    # pattern = r"//upload\.gkzenti\.cn/[\w\d]+/[\w\d]+\.(png|jpg)"
    pattern = r"//upload\.gkzenti\.cn/\w+/\w+\.(?:png|jpg)"
    # pattern = r"//upload\.gkzenti\.cn/\w+/\w+\.(png|jpg)"
    api_endpoint ="https://mian.xiaohe.biz/api/common/uploadByUrl"
    headers = {
        # 'Authorization': f'Bearer {authToken}',
        'Content-Type': 'application/json'
    }
    # 查找所有匹配项
    matches = re.findall(pattern, markdown_text)
    # matches = [
    #     markdown_text
    # ]
    # logger.info(matches)
    # logger.info(f"Found {len(matches)} image URLs:")
    new_markdown = markdown_text
    
    for url in matches:
        # new_markdown += url
        # 调用 POST 接口获取新 image URL
        if(url.count('(')>url.count(')')):
            url = url + ')'
        imageUrl = "https:"+url
        # logger.info(f"imageUrl: {imageUrl}")
        async with aiohttp.ClientSession() as session:
            async with session.post(api_endpoint, json={"imageUrl": imageUrl}, headers=headers) as response:
                data = {}
                if response.status in (200, 201):
                    # 如果返回状态码是200或201，处理响应内容
                    data = await response.json()  # 假设服务器返回JSON格式数据
                    code = data.get("code", {})
                    # logger.info(f"Request response {data}")
                    if code == 200:
                        data = data.get("data", {})
                        new_url = data.get("location")
                        # 用新 URL 替换旧 URL
                        new_markdown = new_markdown.replace(url, new_url)
                        # logger.info(f"new_markdown: {new_markdown}")
                        return new_markdown
                    else:
                        logger.info(f"Request failed with status code: {data}")
                
    return new_markdown
async def process_mianshi(paperId, question, explanation):

    # 解析题目
    try:
        # 创建BeautifulSoup对象
        soup = BeautifulSoup(question, 'html.parser')

        # 获取试卷名称
        title = soup.find('h3', align='center').string
        logger.info(f"试卷名称: {title}")
        year, department = getTitleInfo(title)
        logger.info(f"试卷名称: {title}")
        questions = []

        if len(soup.find_all('h3')) == 3:
            index = 1
            # 获取说明
            introduction = soup.find_all('h3')[1].find_next_sibling(text=True).strip()
            logger.info(f"说明: {introduction}")
            # 获取材料
            material = soup.find_all('h3')[2].find_next().get_text().strip()
            material_points_tags = soup.find_all('h3')[2].find_next_siblings(['p','b'])
            material_points = []
            for tag in material_points_tags:
                if tag.name == 'b' :
                    break
                if tag.get_text(strip=True).startswith(f"第1题"):
                    break
                text_content = tag.get_text(strip=True)
                material_points.append(text_content)
            material = '\n'.join(material_points)
            logger.info(f"材料: {material}")

            # 获取各个试题
            question_start_tags = soup.find_all('b')
            for index, question_start_tag in enumerate(question_start_tags, start=1):
                # question_text = question.find_next_sibling('p').get_text().strip()
                question_tags = question_start_tag.find_next_siblings(['p'])
                question_texts = []
                for _, question in enumerate(question_tags):
                    question_text = question.get_text().strip()
                    question_texts.append(question_text)
                    # logger.info(f"{question_text}")
                    # 检查是否含有 img 标签
                    img_tag = question.find('img')
                    if img_tag:
                        # 获取 src
                        src = img_tag['src']
                        # 转换为 markdown 格式
                        image = f"![]({src})"
                        # logger.info(f"image: {image}")
                        question_texts.append(image)

                question_text = '\n'.join(question_texts)
                question_text = re.sub(r"^第\d+题：", "", question_text)                       
                logger.info(f"{question_text}")
                # logger.info(f"第{i}题: {question_text}")
                question_title = f"{title} 第{index}题"
                questions.append({
                    'comment': paperId,
                    'year': year,
                    'province': department,
                    'departmentId': '0',
                    'department': department,
                    'title': question_title,
                    'origin': title,
                    'introduction': await replace_image_urls(introduction),
                    'material': await replace_image_urls(material),
                    'text': await replace_image_urls(question_text)
                })
        elif len(soup.find_all('h3')) == 1:
            # 获取说明
            introduction = soup.find_all('h2')[0].find_next_sibling(text=True).strip()
            logger.info(f"说明: {introduction}")
            # 提取审题部分紧接着的p标签内容，根据需求调整选择器
            introduction_points_tags = soup.find_all('h2')[0].find_next_siblings(['p','h2'])

            introduction_points = []
            for tag in introduction_points_tags:
                if tag.name == 'h2' :
                    break
                text_content = tag.get_text(strip=True)
                introduction_points.append(text_content)
            material = '\n'.join(introduction_points)
            # # 获取说明
            # material = soup.find_all('h2')[1].find_next().get_text().strip()
            # logger.info(f"材料: {material}")
            question_tags = soup.find_all('h2')[1].find_next_siblings(['p'])
            for index, question in enumerate(question_tags, start=1):
                question_text = question.get_text().strip()
                # 检查是否含有 img 标签
                img_tag = question.find('img')
                if img_tag:
                    # 获取 src
                    src = img_tag['src']
                    # 转换为 markdown 格式
                    image = f"![]({src})"
                    question_text = '\n'.join([question_text, image])
                    
                logger.info(f"{question_text}")
                question_text = re.sub(r"^第\d+题：", "", question_text)
                question_title = f"{title} 第{index}题"
                questions.append({
                    'comment': paperId,
                    'year': year,
                    'province': department,
                    'departmentId': '0',
                    'department': department,
                    'title': question_title,
                    'origin': title,
                    'introduction': await replace_image_urls(introduction),
                    'material': await replace_image_urls(material),
                    'text': await replace_image_urls(question_text)
                })
        

        
    except Exception as e:
            # Rollback on error to maintain consistency and log details for debugging
            # db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
    # 解析答案解析
    analysis_points = []    
    try:
        logger.info("解析答案解析")
        
        # logger.info(f"{explanation}")
        # 从HTML文本创建一个BeautifulSoup对象，使用lxml作为解析器
        soup = BeautifulSoup(explanation, 'html.parser')

        # 找到试卷名称
        exam_title_tag = soup.find('h3', align='center')
        exam_title = exam_title_tag.get_text(strip=True) if exam_title_tag else "无标题"

        logger.info(f"试卷名称: {exam_title}")

        # 初始化列表来存储题目信息
        explanations = []
        index = 1
        for question_block in soup.find_all('blockquote'):
            # 提取题目的标题 （解析与参考答案）
            # question_title_tag = question_block.find_previous('p', string=lambda x: x and "题" in x)
            # question_title = question_title_tag.get_text(strip=True) if question_title_tag else "无题目文字"

            # 提取审题部分紧接着的p标签内容，根据需求调整选择器
            analysis_points_tags = question_block.find_next_siblings(['p','b'])

            analysis_points = []
            for tag in analysis_points_tags:
                text_content = tag.get_text(strip=True)
                # logger.info(f"text_content")
                if text_content.startswith("思维导图") or any(x in text_content for x in ["参考答案"]) :
                    break
                else:
                    analysis_points.append(text_content)

            # 提取思维导图，通常它在<b> 思维导图 </b>后面，与图片对应，假设以img src表示。
            mind_map_tag = question_block.find_next('b', string="思维导图")
            mind_map_image_url = None

            if mind_map_tag:
                img_tag = mind_map_tag.find_next('img')
                mind_map_image_url = img_tag['src'] if img_tag else ""
                mind_map_image_url = await replace_image_urls(mind_map_image_url)
                logger.info(mind_map_image_url)
            # 提取参考答案，在<b> 参考答案 </b>或类似标记后采集相关内容。
            reference_answer_starting_point = question_block.find_next('b', string="参考答案")
            # reference_answer_starters = question_block.find_all('b', string="参考答案")

            reference_answers = []
            if reference_answer_starting_point:
                # ref_answer_tags = reference_answer_starting_point.find_all_next(string=lambda t: t.name == 'p')
                # 在每个<b>标签后找到下一个同级标题或换行分隔
                next_b_tag = reference_answer_starting_point.find_next('b', string=lambda text: text and "题解析与参考答案" in text)
                logger.info(next_b_tag)
                # logger.info("--------")
                ref_answer_tags = reference_answer_starting_point.find_all_next(['p', 'b'])
                ref_ans_txt = ""
                for tag in ref_answer_tags:
                    if tag == next_b_tag:
                        logger.info("----- stop ----- ")
                        break  # 遇到了下一个问题标题，停止
                    if tag.name == 'p' and tag.get_text(strip=True).startswith("&nbsp"):
                        logger.info("----- stop2 ----- ")
                        break  # 遇到了下一个问题标题，停止

                    if tag.name == 'p' and tag.parent.name != "blockquote":
                        ref_ans_txt=tag.get_text(strip=True)
                        # logger.info(ref_ans_txt)
                        reference_answers.append(ref_ans_txt)
                    #if not tag.find_previous('b', string=lambda x: x and "第" in x and "题解析与参考答案" in x):
                    #    reference_answers.append(tag.get_text(strip=True))
                    # else:
                    #    break
                    # if "第" not in ref_ans_txt:  # 在没有找到下一个问题指针前收集所有标准答案P块内容。
                    #    reference_answers.append(tag.get_text(strip=True))
                    # else:
                    #    break

                #reference_answers.append(ref_ans_txt)
            
            explanations.append({
                'analysis': '\n'.join(analysis_points),
                'mindmapUrl': mind_map_image_url,
                'sampleAnswer': '\n'.join(reference_answers),
            })
            index += 1
        # return {"message": "Article processed and data updated successfully."}
    except Exception as e:
        # Rollback on error to maintain consistency and log details for debugging
        # db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    # 将每个 questions 和 explanations 元素的字段合并到一个新的字典中，添加到 interview 列表中
    interviews = []
    for q, e in zip(questions, explanations):
        merged_entry = {**q, **e}
        interviews.append(merged_entry)
    return interviews

async def fetch_html(url, referer: str = None):
    timestamp = int(time.time())
    headers = {
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        # "Cookie": "connect.sid=s%3AFIZCYvlp4vhfk4l5eEq9rr74JCd2an67.uP2a3PFUS8LNC6LVfVaEu2XoG27NIIymPDducAD%2BM48; Hm_lvt_db5c56a1da081947699f2e5bece459c7=1732881600; HMACCOUNT=1A150266D1AAAB30; cls=%E5%85%AC%E5%8A%A1%E5%91%98%E9%9D%A2%E8%AF%95; province=%E5%9B%BD%E8%80%83; Hm_lpvt_db5c56a1da081947699f2e5bece459c7=1734586863",
        "Cookie": f"connect.sid=s%3AasmGihKKO8OTgnFL2y_LgZmYVtts86x6.bbnOMAmmxvMpdGk7ctgHBdB7W4CTwE47z0Ku0x9e9xA; Hm_lvt_db5c56a1da081947699f2e5bece459c7=1734590397; HMACCOUNT=96C839E210B265AA; province=%E5%9B%BD%E8%80%83; cls=%E5%85%AC%E5%8A%A1%E5%91%98%E9%9D%A2%E8%AF%95; Hm_lpvt_db5c56a1da081947699f2e5bece459c7={timestamp}",
        "User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 QuarkPC/1.10.0.169"
    }
    if referer:
        headers['Referer'] = referer
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            return await response.text()

async def getPaperList(url):
    html_content = await fetch_html(url)
    # 使用BeautifulSoup解析HTML内容
    soup = BeautifulSoup(html_content, 'lxml')

    # 找到ID为paperlist的表格
    table = soup.find('table', {'id': 'paperlist'})

    # 初始化结果列表
    papers = []

    # 在指定表格中查找所有符合条件的链接标签<a>，并提取其中的数字部分
    for link in table.find_all('a', href=True):
        # 检查链接是否以/paper/开头以确保匹配设计要求
        if link['href'].startswith('/paper/'):
            # 提取所有以/paper/开头的链接中的数字部分
            number = link['href'].split('/')[-1]
            papers.append(number)

    logger.info(papers)  # 输出结果 ['1727924080287', '1727924080186']
    return papers
async def scrape(listUrl, paperId):
    interview_collection=await get_interview_collection()
    questionUrl = f"https://www.gkzenti.cn/paper/{paperId}"
    question_content = await fetch_html(questionUrl, listUrl)

    questionUrl, explanUrl = await getUrls(paperId)
    logger.info(f"{questionUrl}, {explanUrl}")
    if(questionUrl == None or explanUrl == None):
        raise Exception("Failed to fetch paper urls")
    
    explan_content = await fetch_html(explanUrl, questionUrl)
    interviews = await process_mianshi(paperId, question_content, explan_content)
    if not interviews:
        raise Exception("Failed to process interview")
    for interview in interviews:
        logger.info(interview["title"])
        new_interview = await interview_collection.insert_one(interview)
        created_interview = await interview_collection.find_one({"_id": new_interview.inserted_id})
        # logger.info(f"Created interview: {created_interview}")

def save_paper_id(url, paper_id):

    path = url.split('?')[-1]
    path = unquote(path)
    path = path.replace('cls=', '')
    path = path.replace('=', '')
    path = path.replace('&', '')

    fileName = os.path.join("papers", path + ".txt")
    try:
        os.makedirs(path, exist_ok=True)
        # logger.info(f"Directory '{path}' is created or already exists.")
    except Exception as e:
        logger.info(f"An error occurred while creating the directory: {e}")

    with open(fileName, "a") as file:
        file.write(f"{paper_id}\n")
def load_successful_paper_ids(url):
    path = url.split('?')[-1]
    path = unquote(path)
    path = path.replace('cls=', '')
    path = path.replace('=', '')
    path = path.replace('&', '')
    fileName = os.path.join("papers", path + ".txt")
    try:
        with open(fileName) as file:
            return set(file.read().splitlines())
    except FileNotFoundError:
        return set()        
def generate_pageurls(n):
    #base_url = "https://www.gkzenti.cn/paper?cls=%E5%85%AC%E5%8A%A1%E5%91%98%E9%9D%A2%E8%AF%95&province=%E5%9B%BD%E8%80%83&index="
    # base_url = "https://www.gkzenti.cn/paper?cls=%E5%85%AC%E5%8A%A1%E5%91%98%E9%9D%A2%E8%AF%95&province=%E6%B5%99%E6%B1%9F&index="
    
    # 使用列表推导式生成URL列表
    # urls = [f"{base_url}{i}" for i in reversed(range(1, n + 1))]
    urls = [
        "https://www.gkzenti.cn/paper?cls=%E5%85%AC%E5%8A%A1%E5%91%98%E9%9D%A2%E8%AF%95&province=%E6%B5%99%E6%B1%9F&index=",
        "https://www.gkzenti.cn/paper?cls=%E5%85%AC%E5%8A%A1%E5%91%98%E9%9D%A2%E8%AF%95&province=%E5%B1%B1%E4%B8%9C",
        "https://www.gkzenti.cn/paper?cls=%E5%85%AC%E5%8A%A1%E5%91%98%E9%9D%A2%E8%AF%95&province=%E5%B1%B1%E4%B8%9C&index=2",
        "https://www.gkzenti.cn/paper?cls=%E5%85%AC%E5%8A%A1%E5%91%98%E9%9D%A2%E8%AF%95&province=%E6%B1%9F%E8%8B%8F",
        "https://www.gkzenti.cn/paper?cls=%E5%85%AC%E5%8A%A1%E5%91%98%E9%9D%A2%E8%AF%95&province=%E5%B9%BF%E4%B8%9C",
        "https://www.gkzenti.cn/paper?cls=%E5%85%AC%E5%8A%A1%E5%91%98%E9%9D%A2%E8%AF%95&province=%E5%B9%BF%E4%B8%9C&index=2",
        "https://www.gkzenti.cn/paper?cls=%E5%85%AC%E5%8A%A1%E5%91%98%E9%9D%A2%E8%AF%95&province=%E5%9B%9B%E5%B7%9D",
        "https://www.gkzenti.cn/paper?cls=%E5%85%AC%E5%8A%A1%E5%91%98%E9%9D%A2%E8%AF%95&province=%E7%A6%8F%E5%BB%BA",
        "https://www.gkzenti.cn/paper?cls=%E5%85%AC%E5%8A%A1%E5%91%98%E9%9D%A2%E8%AF%95&province=%E7%A6%8F%E5%BB%BA&index=2",
        "https://www.gkzenti.cn/paper?cls=%E5%85%AC%E5%8A%A1%E5%91%98%E9%9D%A2%E8%AF%95&province=%E5%B9%BF%E8%A5%BF",
        "https://www.gkzenti.cn/paper?cls=%E5%85%AC%E5%8A%A1%E5%91%98%E9%9D%A2%E8%AF%95&province=%E5%AE%89%E5%BE%BD",
        "https://www.gkzenti.cn/paper?cls=%E5%85%AC%E5%8A%A1%E5%91%98%E9%9D%A2%E8%AF%95&province=%E4%B8%8A%E6%B5%B7"


    ]
    return urls

async def periodic_scraping_task():
    url_list = generate_pageurls(1)
    for url in url_list:
        logger.info(url)
        paperIds = await getPaperList(url)
        logger.info(paperIds)
        successful_ids = load_successful_paper_ids(url)
        for paperId in paperIds:
            if paperId not in successful_ids:
                # paperId = '1551781245901o2n'
                # paperId = '1627554027915'
                # paperId = '1647786976704'
                # paperId = '1661056209087'
                try:
                    logger.info(f"Scraping paper with ID: {paperId}")
                    await scrape(url, paperId)
                    save_paper_id(url, paperId)
                except Exception as e:
                    logger.info(f"Error occurred while scraping paper with ID {paperId}: {e}")
                rand = random.randint(1, 20)
                # break
                await asyncio.sleep(50 + rand)  # 每秒钟运行一次任务
        # break

