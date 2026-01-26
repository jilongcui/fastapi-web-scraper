# tasks.py

import re
import aiohttp
import asyncio
import random
import os
from datetime import datetime
from bs4 import BeautifulSoup, NavigableString
from urllib.parse import unquote
from app.logs import get_logger
from fastapi import FastAPI, HTTPException, Depends
from models.user import User  # 从models导入用户模型
from app.database import get_question_collection  # 从app导入数据库函数
from app.tasks_lib import fetch_html, getPaperList, fetch_captcha_svg, image2Code, getUrls
from app.tasks_lib import getTitleInfo, replace_image_urls,save_paper_id,load_successful_paper_ids
from app.tasks_lib import setup_logger

# 为当前模块创建专用logger
logger = setup_logger(__name__)

# 获取保存目录
save_directory = 'papers'

# 公务员行测题目常量配置
CAREER_TYPE = '1'
CAREER_NAME = '公务员'
QUESTION_TYPE = '1'  # 1: 行测 2：申论 3：面试

# 从 explanation 解析 correctAnswer 的增强函数
def parse_correct_answer_from_explanation(explanation):
    """
    从 explanation 文本中使用多个规则解析出 correctAnswer
    返回: 答案字符串(如 'A', 'B', 'AB' 等) 或 None
    """
    if not explanation or not isinstance(explanation, str):
        return None
    
    # 规则1: "故正确选项为A/B/C/D"
    match = re.search(r'故正确选项为([A-D]+)', explanation)
    if match:
        return match.group(1)
    
    # 规则2: "故正确选项选A/B/C/D"
    match = re.search(r'故正确选项选([A-D]+)', explanation)
    if match:
        return match.group(1)
    
    # 规则3: "故本题选A/B/C/D"
    match = re.search(r'故本题选([A-D]+)', explanation)
    if match:
        return match.group(1)
    
    # 规则4: "故本题答案选A/B/C/D"
    match = re.search(r'故本题答案选([A-D]+)', explanation)
    if match:
        return match.group(1)
    
    # 规则5: "答案选A/B/C/D"
    match = re.search(r'答案选([A-D]+)', explanation)
    if match:
        return match.group(1)
    
    # 规则6: "故本题答案为A/B/C/D"
    match = re.search(r'故本题答案为[：:]?([A-D]+)', explanation)
    if match:
        return match.group(1)
    
    # 规则7: "故正确答案为A/B/C/D" (已存在的规则，保持兼容)
    match = re.search(r'故正确答案为[：:]?([A-D]+)', explanation)
    if match:
        return match.group(1)
    
    # 规则8: "表述正确" -> A
    if '表述正确' in explanation:
        return 'A'
    
    # 规则9: "表述错误" -> B
    if '表述错误' in explanation:
        return 'B'
    
    # 规则10: "本题正确" -> A
    if '本题正确' in explanation:
        return 'A'
    
    # 规则11: "本题错误" -> B
    if '本题错误' in explanation:
        return 'B'
    
    return None

# 从网页抓取答案
async def fetch_answers_from_web(paperId):
    """
    从 https://www.gkzenti.cn/answer/{paperId} 抓取答案
    返回: {题号: 答案} 的字典，如 {1: 'C', 2: 'AB', ...} 或 None
    """
    try:
        url = f'https://www.gkzenti.cn/answer/{paperId}'
        logger.info(f"正在从网页抓取答案: {url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=10),
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            ) as response:
                if response.status != 200:
                    logger.error(f"抓取失败: HTTP {response.status}")
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'lxml')
                
                answers = {}
                # 解析答案列表
                for element in soup.select('#printcontent .col-xs-1-5'):
                    text = element.get_text(strip=True)
                    # 匹配格式 "1、C" 或 "1、ABC"
                    match = re.match(r'^(\d+)、([A-D]+)$', text)
                    if match:
                        question_number = int(match.group(1))
                        answer = match.group(2)
                        answers[question_number] = answer
                
                logger.info(f"成功解析 {len(answers)} 个答案")
                return answers if answers else None
    
    except Exception as error:
        logger.error(f"抓取答案失败: {error}")
        return None

# 本题目类型包括：1：常识判断；2：数量关系；3：言语理解与表达；4：判断推理；5：资料分析；6：政治理论；

CONTENT_TYPE = { 
      '1': '常识判断',
      '2': '言语',
      '3': '数量',
      '4': '判断推理',
      '5': '资料分析',
      '6': '政治理论',
      '7': '策略选择'
}

CONTENT_TYPE2 = { 
      '1': '常识',
      '2': '表达',
      '3': '数量',
      '4': '推理',
      '5': '资料',
      '6': '政治',
      '7': '策略'
}

def get_pageurls():
    urls = [
        "https://www.gkzenti.cn/paper?cls=公务员-行测&province=国考",
        "https://www.gkzenti.cn/paper?cls=公务员-行测&province=浙江",
        "https://www.gkzenti.cn/paper?cls=公务员-行测&province=山东",
        "https://www.gkzenti.cn/paper?cls=公务员-行测&province=江苏",
        "https://www.gkzenti.cn/paper?cls=公务员-行测&province=广东",
        "https://www.gkzenti.cn/paper?cls=公务员-行测&province=四川",
        "https://www.gkzenti.cn/paper?cls=公务员-行测&province=福建",
        "https://www.gkzenti.cn/paper?cls=公务员-行测&province=广西",
        "https://www.gkzenti.cn/paper?cls=公务员-行测&province=安徽",
        "https://www.gkzenti.cn/paper?cls=公务员-行测&province=上海",
        "https://www.gkzenti.cn/paper?cls=公务员-行测&province=北京",
        "https://www.gkzenti.cn/paper?cls=公务员-行测&province=辽宁",
        "https://www.gkzenti.cn/paper?cls=公务员-行测&province=天津",
        "https://www.gkzenti.cn/paper?cls=公务员-行测&province=河北",
        "https://www.gkzenti.cn/paper?cls=公务员-行测&province=海南",
        "https://www.gkzenti.cn/paper?cls=公务员-行测&province=河南",
        "https://www.gkzenti.cn/paper?cls=公务员-行测&province=江西",
        "https://www.gkzenti.cn/paper?cls=公务员-行测&province=湖南",
        "https://www.gkzenti.cn/paper?cls=公务员-行测&province=湖北",
        "https://www.gkzenti.cn/paper?cls=公务员-行测&province=山西",
        "https://www.gkzenti.cn/paper?cls=公务员-行测&province=内蒙古",
        "https://www.gkzenti.cn/paper?cls=公务员-行测&province=吉林",
        "https://www.gkzenti.cn/paper?cls=公务员-行测&province=黑龙江",
        "https://www.gkzenti.cn/paper?cls=公务员-行测&province=贵州",
        "https://www.gkzenti.cn/paper?cls=公务员-行测&province=重庆",
        "https://www.gkzenti.cn/paper?cls=公务员-行测&province=陕西",
        "https://www.gkzenti.cn/paper?cls=公务员-行测&province=甘肃",
        "https://www.gkzenti.cn/paper?cls=公务员-行测&province=新疆",
        "https://www.gkzenti.cn/paper?cls=公务员-行测&province=青海",
        "https://www.gkzenti.cn/paper?cls=公务员-行测&province=云南",
        "https://www.gkzenti.cn/paper?cls=公务员-行测&province=宁夏",
        "https://www.gkzenti.cn/paper?cls=公务员-行测&province=西藏",
        "https://www.gkzenti.cn/paper?cls=公务员-行测&province=深圳",
        "https://www.gkzenti.cn/paper?cls=公务员-行测&province=广州",
    ]

    return urls

def _collect_markdown_parts(node):
    parts = []
    if node is None:
        return parts

    if isinstance(node, NavigableString):
        text = str(node)
        if text:
            parts.append(text)
        return parts

    name = getattr(node, 'name', None)
    if name == 'img':
        src = node.get('src')
        if src and src.startswith('//'):
            src = 'https:' + src
        if src:
            parts.append(f"![]({src})")
        # Some pages (or non-HTML5 parsers) can produce a tree like <img>...<img/>...</img>.
        # If we return early here, nested images/text get dropped.
        for child in getattr(node, 'children', []):
            parts.extend(_collect_markdown_parts(child))
        return parts
    if name == 'u':
        # 处理下划线标签，将其转换为下划线字符
        inner_parts = []
        for child in getattr(node, 'children', []):
            inner_parts.extend(_collect_markdown_parts(child))
        inner_text = ''.join(inner_parts)
        # 如果内容只是空格/nbsp，用下划线字符表示填空
        if inner_text.strip() == '' or inner_text.replace('\xa0', '').replace(' ', '') == '':
            parts.append("____")
        else:
            # 有实际内容的下划线，使用 <u> 标签保留
            parts.append(f"<u>{inner_text}</u>")
        return parts
    if name == 'br':
        parts.append("\n")
        return parts

    for child in getattr(node, 'children', []):
        parts.extend(_collect_markdown_parts(child))
    return parts

def node_to_markdown(node):
    text = ''.join(_collect_markdown_parts(node))
    text = text.replace('\xa0', ' ')
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

async def process_question(province, paperId, question, explanation):

    # 解析题目
    try:
        # 创建BeautifulSoup对象
        # Use lxml for more browser-consistent HTML parsing.
        soup = BeautifulSoup(question, 'lxml')

        # 获取试卷名称
        title_tag = soup.find('h3', align='center')
        title = title_tag.string if title_tag else "无标题"
        title = title.replace('\xa0', ' ')
        logger.info(f"试卷名称: {title}")
        year, department, title = getTitleInfo(title)
        title = title.replace('\xa0', ' ')
        logger.info(f"试卷名称: {title}")
        questions = []

        if soup.find('div', class_='subtitle'):
            logger.info("Detected new HTML structure with div.subtitle")
            current_typeName = ""
            current_material = ""

            rows = soup.find_all('div', class_='row')
            for row in rows:
                # 1. 获取子标题subtitle，并提取类别名称typeName
                subtitle_div = row.find('div', class_='subtitle')
                if subtitle_div:
                    subtitle_text = subtitle_div.get_text(strip=True).replace('\xa0', ' ')
                    match = re.search(r'[一二三四五六七八九十]+、(.*?)(?:。|$)', subtitle_text)
                    if match:
                        current_typeName = match.group(1)
                    else:
                        current_typeName = subtitle_text
                    current_material = "" # 切换题型时清空材料
                    logger.info(f"Category: {current_typeName}")
                    continue

                # 2. 处理资料分析的子标题sub2title和材料
                sub2title_div = row.find('div', class_='sub2title')
                if sub2title_div:
                    cols = row.find_all('div', class_='col-xs-12')
                    material_parts = []
                    for col in cols:
                        if 'sub2title' in col.get('class', []):
                            continue
                        for child in col.children:
                            if isinstance(child, str):
                                text = child.strip().replace('\xa0', ' ')
                                if text:
                                    material_parts.append(text)
                                continue
                            if child.name == 'img':
                                src = child.get('src')
                                if src and src.startswith('//'):
                                    src = 'https:' + src
                                if src:
                                    material_parts.append(f"![]({src})")
                                continue
                            text = node_to_markdown(child)
                            if text:
                                material_parts.append(text)
                    current_material = "\n".join(material_parts)
                    continue

                # 3. 获取题目内容text，以及题目选项A,B,C,D
                left_div = row.find('div', class_='left')
                right_div = row.find('div', class_='right')
                if left_div and right_div:
                    index = left_div.get_text(strip=True)
                    question_texts = []
                    options_dict = {}
                    # 打印right_div 所有内容
                    # logger.info(f"Q{index} right_div content: {right_div}")
                    for child in right_div.children:
                        if child.name == 'p':
                            p_text = node_to_markdown(child)
                            if p_text:
                                question_texts.append(p_text)
                        elif child.name == 'div':
                            classes = child.get('class', [])
                            if any(c.startswith('col-xs-') for c in classes):
                                opt_text = node_to_markdown(child)
                                match = re.match(r'^([A-D])、(.*)', opt_text, re.DOTALL)
                                if match:
                                    options_dict[match.group(1)] = match.group(2).strip()

                    question_text = "\n\n".join(question_texts)
                    question_title = f"{title} 第{index}题"
                    
                    # 打印question_text原始内容
                    # logger.info(f"Q{index} Text (raw): {question_text}")
                    logger.info(f"Q{index} md_images={question_text.count('![](')}")
                    # 打印替换之后的内容
                    
                    # logger.info(f"Question Text (replace): {await replace_image_urls(question_text)}")
                    
                    # 根据CONTENT_TYPE定义的内容，把TypeName映射为对应的数字类型
                    type_number = "0"  # 默认类型编号
                    for key, value in CONTENT_TYPE.items():
                        # 并不完全相等，比如value可能是“言语理解”，current_typeName可能是“言语理解与表达”
                        if value in current_typeName:
                            type_number = key
                            break
                    if type_number == "0":
                        for key, value in CONTENT_TYPE2.items():
                        # 并不完全相等，比如value可能是“言语理解”，current_typeName可能是“言语理解与表达”
                            if value in current_typeName:
                                type_number = key
                                break
                    
                    # {A: '选项A内容', B: '选项B内容', ...} 转化为列表 ['','','','']的形式
                    # 并对每个选项内容执行 replace_image_urls转化
                    options_list = [await replace_image_urls(options_dict.get(opt, "")) for opt in ['A', 'B', 'C', 'D']]
                    
                    # 打印
                    questions.append({
                        'comment': paperId,
                        'year': year,
                        'careerType': CAREER_TYPE,
                        'careerName': CAREER_NAME,
                        'questionType': QUESTION_TYPE,
                        'province': province,
                        'departmentId': '0',
                        'department': department,
                        'title': question_title,
                        'origin': title,
                        'index': index,
                        'material': await replace_image_urls(current_material),
                        'text': await replace_image_urls(question_text),
                        'typeId': type_number,
                        'typeName': current_typeName,
                        'options': options_list
                    })
        
    except Exception as e:
            # Rollback on error to maintain consistency and log details for debugging
            # db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
    # 解析答案解析
    explanations = []
    try:
        logger.info("解析答案解析")
        
        logger.info(f"{explanation}")
        # 从HTML文本创建一个BeautifulSoup对象，使用lxml作为解析器
        soup = BeautifulSoup(explanation, 'lxml')

        # 找到试卷名称
        exam_title_tag = soup.find('h3', align='center')
        exam_title = exam_title_tag.get_text(strip=True) if exam_title_tag else "无标题"

        logger.info(f"试卷名称: {exam_title}")

        if soup.find('div', class_='row') and soup.find('div', class_='right'):
            logger.info("Detected new Explanation HTML structure with div.row")
            rows = soup.find_all('div', class_='row')
            for row in rows:
                left = row.find('div', class_='left')
                right = row.find('div', class_='right')
                if left and right:
                    explanation_texts = []
                    correct_answer = ""
                    
                    for child in right.children:
                        if child.name == 'p':
                            md_text = node_to_markdown(child)
                            if md_text:
                                explanation_texts.append(md_text)

                            # Extract correct answer from plain text to avoid markdown noise.
                            plain_text = child.get_text(" ", strip=True).replace('\xa0', ' ')
                            if not correct_answer:
                                correct_answer = parse_correct_answer_from_explanation(plain_text) or ""
                        elif child.name == 'img':
                             img_md = node_to_markdown(child)
                             if img_md:
                                 explanation_texts.append(img_md)
                        elif isinstance(child, str) and child.strip():
                             explanation_texts.append(child.strip().replace('\xa0', ' '))

                    full_explanation = "\n\n".join([t for t in explanation_texts if t]).strip()
                    
                    explanations.append({
                        'explanation': await replace_image_urls(full_explanation),
                        'correctAnswer': correct_answer,
                        'allowMultipleSelections': len(correct_answer) > 1 if correct_answer else False
                    })
        else:
            # 初始化列表来存储题目信息
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
                    # 'mindmapUrl': mind_map_image_url,
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
    logger.info(f"Questions: {len(questions)}, Explanations: {len(explanations)}")
    
    count = min(len(questions), len(explanations))
    for i in range(count):
        merged_entry = {**questions[i], **explanations[i]}
        interviews.append(merged_entry)
    
    # 检查是否有空的 correctAnswer，如果有则从网页抓取
    empty_answer_count = sum(1 for item in interviews if not item.get('correctAnswer'))
    if empty_answer_count > 0:
        logger.info(f"发现 {empty_answer_count} 个题目答案为空，尝试从网页抓取答案...")
        web_answers = await fetch_answers_from_web(paperId)
        
        if web_answers:
            filled_count = 0
            for item in interviews:
                if not item.get('correctAnswer') and item.get('index'):
                    question_number = item['index']
                    if question_number in web_answers:
                        item['correctAnswer'] = web_answers[question_number]
                        item['allowMultipleSelections'] = len(web_answers[question_number]) > 1
                        filled_count += 1
            logger.info(f"从网页成功填充了 {filled_count} 个答案")
        else:
            logger.warning(f"无法从网页获取答案，paperId: {paperId}")
    
    logger.info(interviews)
    return interviews


async def scrape_process(listUrl, paperId, province):
    question_collection=await get_question_collection()
    questionUrl = f"https://www.gkzenti.cn/paper/{paperId}"
    question_content = await fetch_html(questionUrl, listUrl)
    await asyncio.sleep(5)  # 每秒钟运行一次任务
    questionUrl, explanUrl = await getUrls(paperId)
    logger.info(f"{questionUrl}, {explanUrl}")
    if(questionUrl == None or explanUrl == None):
        raise Exception("Failed to fetch paper urls")
    await asyncio.sleep(5)  
    explan_content = await fetch_html(explanUrl, questionUrl)
    questions = await process_question(province, paperId, question_content, explan_content)
    if not questions:
        raise Exception("Failed to process questions")
    for question in questions:
        logger.info(question["title"])
        # 添加创建时间和更新时间
        now = datetime.now()
        question['createTime'] = now
        question['updateTime'] = now
        new_question = await question_collection.insert_one(question)
        created_question = await question_collection.find_one({"_id": new_question.inserted_id})
        # logger.info(f"Created question: {created_question}")


async def periodic_scraping_question_task():
    try:
        os.makedirs(save_directory, exist_ok=True)
        # logger.info(f"Directory '{path}' is created or already exists.")
    except Exception as e:
        logger.info(f"An error occurred while creating the directory: {e}")

    url_list = get_pageurls()
    for url in url_list:
        logger.info(url)
    
        # 提取URL中的省份信息
        # 例如: "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=贵州" → "贵州"
        # 例如: "https://www.gkzenti.cn/paper?cls=事业单位-职测&province=浙江&index=2" → "浙江"
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
                # paperId = '1746428264151'
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
                await asyncio.sleep(10 + rand)  # 每秒钟运行一次任务
                # break
        # break

