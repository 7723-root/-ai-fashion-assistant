# 文件名：app.py
import streamlit as st
from transformers import pipeline
from PIL import Image
import requests
import json
import base64
from io import BytesIO
import os
from datetime import datetime

# 设置页面配置
st.set_page_config(
    page_title="AI穿搭小助手",
    page_icon="👚",
    layout="wide"
)

# 百度智能云认证信息（替换为你自己的）
API_KEY = st.secrets["API_KEY"]
SECRET_KEY = st.secrets["SECRET_KEY"]
# 初始化历史记录目录
if not os.path.exists("history"):
    os.makedirs("history")

# 加载Hugging Face的文本生成模型
@st.cache_resource  # 缓存模型加载
def load_text_model():
    return pipeline("text-generation", model="gpt2")

# 获取百度API的访问令牌
@st.cache_data(ttl=21600)  # 缓存2小时
def get_access_token():
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={API_KEY}&client_secret={SECRET_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        st.error("获取百度API令牌失败，请检查密钥")
        return None

# 功能1：基于文本的穿搭推荐
def generate_outfit(occasion, weather, style=None):
    model = load_text_model()
    prompt = f"为{weather}天气的{occasion}场合推荐一套{style if style else ''}风格的穿搭："
    response = model(prompt, max_length=150, num_return_sequences=1)
    return response[0]['generated_text']

# 功能2：图像分类（使用百度API）
def classify_image(image):
    access_token = get_access_token()
    if not access_token:
        return "认证失败"
    
    # 将PIL图像转换为base64
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    # 调用百度图像分类API
    url = f"https://aip.baidubce.com/rest/2.0/image-classify/v2/advanced_general?access_token={access_token}"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {'image': img_base64}
    
    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        result = response.json()
        if 'result' in result and len(result['result']) > 0:
            return result['result'][0]['keyword']
        else:
            return "未识别出服装类型"
    else:
        return f"API调用失败: {response.text}"

# 功能3：根据图片推荐穿搭
def recommend_outfit_by_image(image, weather, occasion):
    clothing_type = classify_image(image)
    model = load_text_model()
    prompt = f"为{weather}天气的{occasion}场合，推荐一套包含{clothing_type}的穿搭："
    response = model(prompt, max_length=150, num_return_sequences=1)
    return response[0]['generated_text'], clothing_type

# 功能4：保存穿搭历史（使用文件存储）
def save_history(user_id, occasion, weather, style, recommendation, clothing_type=None):
    # 构建历史记录
    history_entry = {
        "user_id": user_id,
        "occasion": occasion,
        "weather": weather,
        "style": style,
        "recommendation": recommendation,
        "clothing_type": clothing_type,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # 保存到JSON文件
    filename = f"history/{user_id}_history.json"
    
    # 如果文件已存在，读取并追加
    if os.path.exists(filename):
        with open(filename, "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
    else:
        data = []
    
    data.append(history_entry)
    
    # 写入更新后的文件
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)
    
    return True

# 读取历史记录
def load_history(user_id):
    filename = f"history/{user_id}_history.json"
    if os.path.exists(filename):
        with open(filename, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

# 网页界面
st.title("AI穿搭小助手 👚")
st.markdown("智能推荐适合各种场合和天气的穿搭，让你每天都时尚得体！")

# 用户ID（简化实现）
user_id = st.session_state.get("user_id", str(hash(str(datetime.now())) % 1000000))
st.session_state.user_id = user_id

# 侧边栏
with st.sidebar:
    st.header("设置")
    style_options = ["休闲", "正式", "时尚", "运动", "复古", "简约", "甜美", "个性"]
    selected_style = st.selectbox("偏好风格", style_options)
    
    st.subheader("使用说明")
    st.markdown("1. 选择场合和天气条件")
    st.markdown("2. 上传你的服装图片（可选）")
    st.markdown("3. 点击生成推荐按钮")
    st.markdown("4. 保存你喜欢的穿搭方案")
    
    st.divider()
    st.markdown("💡 提示：上传服装图片后，AI会根据你已有的衣服进行搭配推荐")

# 主界面
tab1, tab2, tab3 = st.tabs(["文本推荐", "图片推荐", "历史记录"])

with tab1:
    st.subheader("基于文本的穿搭推荐")
    col1, col2 = st.columns(2)
    
    with col1:
        occasion = st.selectbox("场合", ["日常", "工作", "派对", "运动", "约会", "旅行", "居家"])
    
    with col2:
        weather = st.selectbox("天气", ["炎热", "温暖", "凉爽", "寒冷", "雨天", "雪天"])
    
    if st.button("生成推荐", key="text_recommend"):
        with st.spinner("AI正在思考中..."):
            recommendation = generate_outfit(occasion, weather, selected_style)
            st.success("推荐生成成功！")
            st.markdown(f"### 推荐穿搭方案：")
            st.write(recommendation)
            
            # 保存历史记录
            save_history(user_id, occasion, weather, selected_style, recommendation)

with tab2:
    st.subheader("基于图片的穿搭推荐")
    uploaded_file = st.file_uploader("上传你的衣服图片", type=["jpg", "png", "jpeg"])
    
    col1, col2 = st.columns(2)
    
    with col1:
        occasion_img = st.selectbox("场合", ["日常", "工作", "派对", "运动", "约会", "旅行", "居家"], key="img_occasion")
    
    with col2:
        weather_img = st.selectbox("天气", ["炎热", "温暖", "凉爽", "寒冷", "雨天", "雪天"], key="img_weather")
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption='上传的图片', use_column_width=True)
        
        if st.button("生成推荐", key="image_recommend"):
            with st.spinner("分析图片并生成穿搭方案..."):
                recommendation, clothing_type = recommend_outfit_by_image(image, weather_img, occasion_img)
                st.success("推荐生成成功！")
                st.markdown(f"### 基于 {clothing_type} 的穿搭方案：")
                st.write(recommendation)
                
                # 保存历史记录
                save_history(user_id, occasion_img, weather_img, selected_style, recommendation, clothing_type)

with tab3:
    st.subheader("我的穿搭历史")
    history = load_history(user_id)
    
    if history:
        for i, entry in enumerate(reversed(history)):
            with st.expander(f"穿搭方案 #{len(history) - i}"):
                st.markdown(f"**场合**：{entry['occasion']}")
                st.markdown(f"**天气**：{entry['weather']}")
                if entry.get('clothing_type'):
                    st.markdown(f"**基础服装**：{entry['clothing_type']}")
                st.markdown(f"**风格**：{entry['style']}")
                st.write(entry['recommendation'])
                st.markdown(f"🕒 {entry['timestamp']}")
    else:
        st.info("你还没有任何穿搭记录，请先使用上方的功能生成推荐")

# 页脚
st.divider()
st.caption("© 2025 AI穿搭小助手 | 使用Streamlit和百度智能云构建")