# tasks.py

import re
import aiohttp
import asyncio
import random
import os
from bs4 import BeautifulSoup
from urllib.parse import unquote
from app.logs import get_logger
from fastapi import FastAPI, HTTPException, Depends
from models.user import User  # 从models导入用户模型
from app.database import get_interview_collection  # 从app导入数据库函数
from app.tasks_lib import fetch_html, getPaperList, fetch_captcha_svg, image2Code, getUrls
from app.tasks_lib import getTitleInfo, replace_image_urls,save_paper_id,load_successful_paper_ids
from app.tasks_lib import setup_logger

# 为当前模块创建专用logger
logger = setup_logger(__name__)

# 获取保存目录
save_directory = 'papers'


def get_pageurls():
    urls = [
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=国家",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=国考",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=浙江",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=浙江&index=2",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=浙江&index=3",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=山东",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=山东&index=2",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=山东&index=3",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=山东&index=4",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=山东&index=6",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=江苏",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=江苏&index=2",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=广东",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=广东&index=2",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=广东&index=3",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=四川",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=四川&index=2",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=福建",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=福建&index=2",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=福建&index=3",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province广西",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province广西&index=2",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=安徽",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=安徽&index=2",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=安徽&index=3",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=上海",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=上海&index=2",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=北京",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=辽宁",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=天津",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=河北",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=河北&index=2",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=海南",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=河南",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=河南&index=2",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=河南&index=3",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=江西",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=江西&index=2",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=湖南",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=湖南&index=2",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=湖北",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=湖北&index=2",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=山西",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=山西&index=2",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=山西&index=3",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=内蒙古",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=内蒙古&index=2",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=内蒙古&index=3",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=内蒙古&index=4",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=吉林",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=吉林&index=2",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=黑龙江",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=贵州",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=贵州&index=2",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=贵州&index=3",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=贵州&index=4",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=重庆",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=重庆&index=2",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=陕西",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=陕西&index=2",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=甘肃",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=云南&index=2",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=新疆",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=宁夏&index=2",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=青海",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=西藏&index=2",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=深圳",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=其他",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=三支一扶",
        "https://www.gkzenti.cn/paper?cls=事业单位面试&province=三支一扶&index=2",

    ]

    return urls

async def process_mianshi(province, paperId, question, explanation):

    # 解析题目
    try:
        # 创建BeautifulSoup对象
        soup = BeautifulSoup(question, 'html.parser')

        # 获取试卷名称
        title = soup.find('h3', align='center').string
        logger.info(f"试卷名称: {title}")
        year, department, title = getTitleInfo(title)
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
                        logger.info(f"image: {image}")
                        question_texts.append(image)

                question_text = '\n'.join(question_texts)
                question_text = re.sub(r"^第\d+题：", "", question_text)                       
                logger.info(f"{question_text}")
                logger.info(f"第{index}题: {question_text}")
                question_title = f"{title} 第{index}题"
                questions.append({
                    'comment': paperId,
                    'year': year,
                    'careerId': '2',
                    'careerName': '事业单位',
                    'province': province,
                    'departmentId': '0',
                    'department': department,
                    'title': question_title,
                    'origin': title,
                    'introduction': await replace_image_urls(introduction),
                    'material': await replace_image_urls(material),
                    'text': await replace_image_urls(question_text)
                })
        elif len(soup.find_all('h3')) == 1 and len(soup.find_all('h2')) >=2:
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
                    'careerId': '2',
                    'careerName': '事业单位',
                    'province': province,
                    'departmentId': '0',
                    'department': department,
                    'title': question_title,
                    'origin': title,
                    'introduction': await replace_image_urls(introduction),
                    'material': await replace_image_urls(material),
                    'text': await replace_image_urls(question_text)
                })
        elif len(soup.find_all('h3')) == 1 and len(soup.find_all('h2')) <=1:
            # 对于这种结构，题目内容在div内部，需要找到包含题目的div
            introduction = ""
            material = ""
            
            # 找到包含题目的div或直接查找所有b标签（题目标识）
            question_tags = soup.find_all('b')
            
            for index, question_start_tag in enumerate(question_tags, start=1):
                # 获取每个题目的内容
                question_texts = []
                # 找到b标签后面的p标签内容，直到下一个b标签
                next_tags = question_start_tag.find_next_siblings(['p', 'b'])
                
                for tag in next_tags:
                    if tag.name == 'b':  # 遇到下一个题目标识，停止
                        break
                    question_text = tag.get_text().strip()
                    if question_text:  # 只添加非空内容
                        question_texts.append(question_text)
                        
                    # 检查是否含有 img 标签
                    img_tag = tag.find('img')
                    if img_tag:
                        # 获取 src
                        src = img_tag['src']
                        # 转换为 markdown 格式
                        image = f"![]({src})"
                        logger.info(f"image: {image}")
                        question_texts.append(image)

                question_text = '\n'.join(question_texts)
                question_text = re.sub(r"^第\d+题：", "", question_text)                       
                logger.info(f"第{index}题: {question_text}")
                question_title = f"{title} 第{index}题"
                questions.append({
                    'comment': paperId,
                    'year': year,
                    'careerId': '2',
                    'careerName': '事业单位',
                    'province': province,
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
        
        logger.info(f"{explanation}")
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
            analysis_points_tags = question_block.find_next_siblings(['p','b', 'br'])

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
            # 提取参考答案，在<b> 参考答案 </b>或<b> 参考解析 </b>等类似标记后采集相关内容。
            reference_answer_starting_point = question_block.find_next('b', string=lambda text: text and ("参考答案" in text or "参考解析" in text))
            # reference_answer_starters = question_block.find_all('b', string="参考答案")

            reference_answers = []
            if reference_answer_starting_point:
                # ref_answer_tags = reference_answer_starting_point.find_all_next(string=lambda t: t.name == 'p')
                # 在每个<b>标签后找到下一个同级标题或换行分隔
                next_b_tag = reference_answer_starting_point.find_next('b', string=lambda text: text and "题解析与参考答案" in text)
                logger.info(next_b_tag)
                logger.info("--------")
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
                    if tag.name == 'footer':
                        logger.info("----- footer stop ----- ")
                        break  # 遇到了下一个问题标题，停止
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
                'sampleAnswer': '\n'.join(reference_answers).split("\n\n\n欢迎使用公开真题库")[0], #  移除"\n\n\n欢迎使用公开真题库" 以及后面的内容
            })
            index += 1
        # return {"message": "Article processed and data updated successfully."}
    except Exception as e:
        # Rollback on error to maintain consistency and log details for debugging
        # db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    # 将每个 questions 和 explanations 元素的字段合并到一个新的字典中，添加到 interview 列表中
    interviews = []
    logger.info("1")
    for q, e in zip(questions, explanations):
        merged_entry = {**q, **e}
        interviews.append(merged_entry)
    logger.info(interviews)
    return interviews


async def scrape_process(listUrl, paperId, province):
    interview_collection=await get_interview_collection()
    questionUrl = f"https://www.gkzenti.cn/paper/{paperId}"
    question_content = await fetch_html(questionUrl, listUrl)
    await asyncio.sleep(5)  # 每秒钟运行一次任务
    questionUrl, explanUrl = await getUrls(paperId)
    logger.info(f"{questionUrl}, {explanUrl}")
    if(questionUrl == None or explanUrl == None):
        raise Exception("Failed to fetch paper urls")
    await asyncio.sleep(5)  
    explan_content = await fetch_html(explanUrl, questionUrl)
    interviews = await process_mianshi(province, paperId, question_content, explan_content)
    if not interviews:
        raise Exception("Failed to process interview")
    for interview in interviews:
        logger.info(interview["title"])
        new_interview = await interview_collection.insert_one(interview)
        created_interview = await interview_collection.find_one({"_id": new_interview.inserted_id})
        # logger.info(f"Created interview: {created_interview}")


async def periodic_scraping_task():
    try:
        os.makedirs(save_directory, exist_ok=True)
        # logger.info(f"Directory '{path}' is created or already exists.")
    except Exception as e:
        logger.info(f"An error occurred while creating the directory: {e}")

    url_list = get_pageurls()
    for url in url_list:
        logger.info(url)
    
        # 提取URL中的省份信息
        # 例如: "https://www.gkzenti.cn/paper?cls=事业单位面试&province=贵州" → "贵州"
        # 例如: "https://www.gkzenti.cn/paper?cls=事业单位面试&province=浙江&index=2" → "浙江"
        province = url.split("province=")[-1].split("&")[0] if "province=" in url else "未知省份"
        # URL解码省份名称
        province = unquote(province)
        logger.info(f"正在处理省份: {province}")
        
        paperIds = await getPaperList(url)
        logger.info(paperIds)
        successful_ids = load_successful_paper_ids(url, save_directory)
        for paperId in paperIds:
            if paperId not in successful_ids:
                # paperId = '1668003216766'
                # paperId = '1702961776894'
                # paperId = '1667998867772'
                max_retries = 3
                success = False
                last_error = None
                
                for attempt in range(max_retries):
                    try:
                        logger.info(f"Scraping paper with ID: {paperId} (attempt {attempt + 1}/{max_retries})")
                        await scrape_process(url, paperId, province)
                        save_paper_id(url, paperId, save_directory)
                        success = True
                        break
                    except Exception as e:
                        last_error = e
                        logger.info(f"Attempt {attempt + 1} failed for paper ID {paperId}: {e}")
                        if attempt < max_retries - 1:  # 不是最后一次尝试
                            await asyncio.sleep(5)  # 重试前等待5秒
                
                if not success:
                    logger.info(f"Failed to scrape paper ID {paperId} after {max_retries} attempts. Last error: {last_error}")
                
                rand = random.randint(1, 10)
                await asyncio.sleep(30 + rand)  # 每秒钟运行一次任务
                # break
        # break

