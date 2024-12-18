# tasks.py

import aiohttp
import asyncio
# import requests
import json
import base64
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, Depends
from .models import Word, Base
from .database import engine, SessionLocal, get_db

async def fetch_captcha_svg(url, headers):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                svg_data = await response.text()
                print(f"Fetched SVG: {svg_data[:100]}...")  # 打印前100个字符以示例
                return svg_data
            else:
                print(f"Failed to fetch SVG, status code: {response.status}")
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
    api_endpoint = "https://mianshi.xiaohe.biz/api/interview-set/svg2Answer"
    headers = {
        # 'Authentication': f'{authToken}',  # 确保替换为你的真实认证令牌
        'Content-Type': 'application/json'
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(api_endpoint, json={"imageUrl": imageUrl}, headers=headers) as response:
            data = {}
            if response.status in (200, 201):
                # 如果返回状态码是200或201，处理响应内容
                print("Request successful")
                data = await response.json()  # 假设服务器返回JSON格式数据
                code = data.get("code", {})
                if code == 200:
                    data = data.get("data", {})
                else:
                    print(f"Request failed with status code: {response.status}")
            return data
# 定义API端点和图像URL

imageUrl = "your_image_url_here"


async def getUrls(paperId:str) -> dict:
    # 抓取svgStr
    url = "https://www.gkzenti.cn/captcha/math"
    headers = {
        'Cookie': "Hm_lvt_db5c56a1da081947699f2e5bece459c7=1733669135; connect.sid=s%3AbcN_EF1Gj31QqEsKDM4YSwKlWQCknmZo.hn4pORqPpYPaVMREJ677oaYk317aZ2QgA2%2B88Hlk2kQ; cls=%E8%A1%8C%E6%B5%8B; province=%E5%9B%BD%E8%80%83; HMACCOUNT=2CF09B05167D4A59; Hm_lpvt_db5c56a1da081947699f2e5bece459c7=1734055038","User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 QuarkPC/1.10.0.169"
    }
    svgStr = await fetch_captcha_svg(url, headers)
    # 将转义字符移除
    svg_string = svgStr.replace('\"', '"')

    # 将修正后的SVG字符串编码为UTF-8字节
    svg_bytes = svg_string.encode('utf-8')
    
    # 对字节进行Base64编码
    base64_encoded_svg = base64.b64encode(svg_bytes).decode('utf-8')

    # 创建Data URI格式
    data_uri = f'data:image/svg+xml;base64,{base64_encoded_svg}'
    
    # 假设image2Answer是在其他地方定义的函数，用于处理encoded data和authentication token。
    data = image2Code(data_uri)
    code = data.get("answer")
    paperUrl = f"https://www.gkzenti.cn/paper/{paperId}"
    explanUrl = f"https://www.gkzenti.cn/explain/{paperId}?mathcode={code}"
    return {
        # "data_uri": data_uri,
        "content": data.get("content"),
        "code": code,
        "paperUrl" : paperUrl,
        "explanUrl" : explanUrl,
    }

async def process_mianshi(question, explanation, db: SessionLocal = Depends(get_db)):

    # 解析题目
    try:
        # 创建BeautifulSoup对象
        soup = BeautifulSoup(question, 'html.parser')

        # 获取试卷名称
        title = soup.find('h3', align='center').string
        print(f"试卷名称: {title}")

        # 获取说明
        introduction = soup.find_all('h3')[1].find_next_sibling(text=True).strip()
        print(f"说明: {introduction}")

        # 获取说明
        material = soup.find_all('h3')[2].find_next().get_text().strip()
        print(f"材料: {material}")

        questions = []
        # 获取各个试题
        question_tags = soup.find_all('b')
        for i, question in enumerate(question_tags, start=1):
            question_text = question.find_next_sibling('p').get_text().strip()
            # print(f"第{i}题: {question_text}")
            question_title = f"{title} 第{index}题"
            questions.append({
                'title': question_title,
                'origin': title,
                'introduction': introduction,
                'material': material,
                'text': question_text
            })
    except Exception as e:
            # Rollback on error to maintain consistency and log details for debugging
            # db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
    # 解析答案解析
    analysis_points = []    
    try:
        print("解析答案解析")
        # print(f"{paper.explanation}")
        # 从HTML文本创建一个BeautifulSoup对象，使用lxml作为解析器
        soup = BeautifulSoup(explanation, 'html.parser')

        # 找到试卷名称
        exam_title_tag = soup.find('h3', align='center')
        exam_title = exam_title_tag.get_text(strip=True) if exam_title_tag else "无标题"

        print(f"试卷名称: {exam_title}")

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

            # 提取参考答案，在<b> 参考答案 </b>或类似标记后采集相关内容。
            reference_answer_starting_point = question_block.find_next('b', string="参考答案")
            # reference_answer_starters = question_block.find_all('b', string="参考答案")

            reference_answers = []
            if reference_answer_starting_point:
                # ref_answer_tags = reference_answer_starting_point.find_all_next(string=lambda t: t.name == 'p')
                # 在每个<b>标签后找到下一个同级标题或换行分隔
                next_b_tag = reference_answer_starting_point.find_next('b', string=lambda text: text and "题解析与参考答案" in text)
                # print(next_b_tag)
                # print("--------")
                ref_answer_tags = reference_answer_starting_point.find_all_next(['p', 'b'])
                ref_ans_txt = ""
                for tag in ref_answer_tags:
                    if tag == next_b_tag:
                        print("----- stop ----- ")
                        break  # 遇到了下一个问题标题，停止
                    if tag.name == 'p' and tag.get_text(strip=True) == "&nbsp":
                        print("----- stop ----- ")
                        break  # 遇到了下一个问题标题，停止

                    if tag.name == 'p' and tag.parent.name != "blockquote":
                        ref_ans_txt=tag.get_text(strip=True)
                        # print(ref_ans_txt)
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

async def fetch_html(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
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

    print(papers)  # 输出结果 ['1727924080287', '1727924080186']
    return papers
async def scrape(paperId):
    questionUrl, explanUrl = await getUrls(paperId)
    question_content = await fetch_html(questionUrl)
    explan_content = await fetch_html(explanUrl)
    process_mianshi(question_content, explan_content)

async def periodic_scraping_task():
    paperIds = getPaperList()
    for paperId in paperIds:
        await scrape(paperId)  # Replace with your target URL
        await asyncio.sleep(10)  # 每小时运行一次任务

