import streamlit as st
import pandas as pd
import io

# --- 页面基础设置 ---
st.set_page_config(page_title="评论自动打标工具", layout="wide", page_icon="🏷️")

# --- 核心分析函数 ---
def analyze_reviews(df_main, df_good, df_bad, col_review, col_rating):
    """
    根据星级分流，分别匹配好评库和差评库
    """
    # 1. 准备标签库 (转为列表并过滤空值)
    # 假设标签都在第一列
    good_tags = df_good.iloc[:, 0].dropna().astype(str).tolist()
    bad_tags = df_bad.iloc[:, 0].dropna().astype(str).tolist()
    
    # 2. 定义单行处理逻辑
    def get_tag(row):
        # 获取评论内容，转为字符串，如果是空则为空字符串
        content = str(row[col_review]) if pd.notna(row[col_review]) else ""
        
        # 获取星级
        try:
            rating = float(row[col_rating])
        except:
            return None # 星级格式不对，跳过

        matched_tag = None
        target_tags = []

        # --- 核心逻辑：星级分流 ---
        if rating >= 4:
            # 4-5星：只匹配好评词
            target_tags = good_tags
        elif rating <= 3:
            # 1-3星：只匹配差评词
            target_tags = bad_tags
        else:
            return None # 其他情况不打标

        # --- 关键词匹配 ---
        # 遍历对应的标签库，看哪个词出现在了评论里
        for tag in target_tags:
            if tag in content:
                matched_tag = tag
                break # 找到第一个匹配的就停止 (如需匹配多个可修改此处)
        
        return matched_tag

    # 3. 应用逻辑到每一行
    # 使用 .copy() 防止报警
    df_result = df_main.copy()
    df_result['分析标签'] = df_result.apply(get_tag, axis=1)
    
    return df_result

# --- 界面显示 ---
st.title("🏷️ 亚马逊评论自动打标神器")
st.markdown("""
**使用说明：**
请上传一个 **Excel (.xlsx)** 文件，文件内必须包含 **3个工作表 (Sheets)**：
1.  **Sheet 1 (数据源)**：包含顾客评论和星级的原始数据。
2.  **Sheet 2 (好评库)**：包含所有好评标签（如：舒适、透气）。
3.  **Sheet 3 (差评库)**：包含所有差评标签（如：偏小、魔术贴失效）。
""")

# --- 文件上传区 ---
uploaded_file = st.file_uploader("请将整理好的 Excel 文件拖拽到此处", type=['xlsx'])

if uploaded_file:
    try:
        # 读取 Excel 文件
        xls = pd.ExcelFile(uploaded_file)
        sheet_names = xls.sheet_names
        
        if len(sheet_names) < 3:
            st.error(f"❌ 文件格式错误：检测到只有 {len(sheet_names)} 个Sheet。请确保文件包含：数据表、好评表、差评表。")
        else:
            # 读取三个表
            df_main = pd.read_excel(xls, sheet_name=0)      # 主数据
            df_good = pd.read_excel(xls, sheet_name=1)      # 好评库
            df_bad = pd.read_excel(xls, sheet_name=2)       # 差评库
            
            st.success(f"✅ 文件读取成功！包含 {len(df_main)} 条评论数据。")
            
            # --- 列名映射配置区 ---
            st.write("---")
            st.subheader("🛠️ 第一步：请确认关键列名")
            
            col1, col2 = st.columns(2)
            
            # 获取所有列名
            all_columns = df_main.columns.tolist()
            
            with col1:
                # 智能预选：查找包含 "内容", "评论", "Review" 的列
                default_review = next((i for i, c in enumerate(all_columns) if any(x in str(c).lower() for x in ['内容', '评论', 'review', 'content'])), 0)
                selected_review_col = st.selectbox("请选择【评论内容】所在的列：", all_columns, index=default_review)
            
            with col2:
                # 智能预选：查找包含 "星", "分", "Rating" 的列
                default_rating = next((i for i, c in enumerate(all_columns) if any(x in str(c).lower() for x in ['星', '分', 'rating'])), 0)
                selected_rating_col = st.selectbox("请选择【星级/评分】所在的列：", all_columns, index=default_rating)

            # --- 执行分析 ---
            if st.button("🚀 开始自动打标", type="primary"):
                with st.spinner('正在逐条分析评论，请稍候...'):
                    # 调用分析函数
                    result_df = analyze_reviews(df_main, df_good, df_bad, selected_review_col, selected_rating_col)
                    
                    # 统计结果
                    tagged_count = result_df['分析标签'].notna().sum()
                    total_count = len(result_df)
                    
                    st.write("---")
                    st.subheader("📊 分析结果")
                    st.info(f"共分析 {total_count} 条数据，成功打标 **{tagged_count}** 条。")
                    
                    # 预览前 10 行
                    st.dataframe(result_df.head(10))
                    
                    # --- 下载区 ---
                    output = io.BytesIO()
                    # 导出为 CSV，使用 utf-8-sig 防止中文乱码
                    result_df.to_csv(output, index=False, encoding='utf-8-sig')
                    output.seek(0)
                    
                    st.download_button(
                        label="📥 下载打标后的 CSV 文件",
                        data=output,
                        file_name="Review_Analysis_Result.csv",
                        mime="text/csv"
                    )

    except Exception as e:
        st.error(f"发生未知错误，请检查文件格式: {e}")
