import streamlit as st
import pandas as pd
import io

# --- 核心配置 ---
# 这里定义你的列名，如果表格列名不同，请修改这里
COL_COMMENT = '顾客评论'  # 评论内容的列名
COL_RATING = '星级'      # 星级的列名
COL_OUTPUT = '分析标签'  # 新生成的标签列名

def process_data(file_buffer):
    """
    核心处理逻辑：读取上传的Excel流，进行打标，返回处理后的DataFrame
    """
    try:
        # 1. 读取所有需要的Sheet
        # 这里的sheet_name=None会读取所有sheet，或者指定索引0,1,2
        xls = pd.ExcelFile(file_buffer)
        
        # 假设 Sheet1=数据, Sheet2=好评库, Sheet3=差评库
        # 如果你的Sheet名是固定的，建议直接用 names=['Sheet1', '好评', '差评']
        sheet_names = xls.sheet_names
        if len(sheet_names) < 3:
            return None, "错误：Excel文件必须至少包含3个Sheet（数据表、好评表、差评表）"
            
        df_main = pd.read_excel(xls, sheet_name=0)      # 主数据
        df_good_tags = pd.read_excel(xls, sheet_name=1) # 好评库
        df_bad_tags = pd.read_excel(xls, sheet_name=2)  # 差评库
        
        # 检查必要列是否存在
        if COL_COMMENT not in df_main.columns or COL_RATING not in df_main.columns:
            return None, f"错误：第一张表中未找到列名 '{COL_COMMENT}' 或 '{COL_RATING}'"

        # 提取标签列表（转为字符串并去空）
        good_tags = df_good_tags.iloc[:, 0].dropna().astype(str).tolist()
        bad_tags = df_bad_tags.iloc[:, 0].dropna().astype(str).tolist()

    except Exception as e:
        return None, f"文件读取失败: {str(e)}"

    # 2. 定义单行打标逻辑
    def get_tag(row):
        comment = str(row[COL_COMMENT]) if pd.notna(row[COL_COMMENT]) else ""
        rating = row[COL_RATING]
        
        if not comment: return None
        
        # 确保星级是数字
        try:
            rating = float(rating)
        except:
            return None 

        # 逻辑分流：1-3星查差评库，4-5星查好评库
        target_tags = []
        if 4 <= rating <= 5:
            target_tags = good_tags
        elif 1 <= rating <= 3:
            target_tags = bad_tags
        else:
            return None # 星级异常
            
        # 匹配标签
        for tag in target_tags:
            if tag in comment:
                return tag # 找到第一个即返回
        return None # 没匹配到

    # 3. 应用逻辑
    df_main[COL_OUTPUT] = df_main.apply(get_tag, axis=1)
    
    return df_main, "Success"

# --- 网页界面构建 (Streamlit) ---
st.set_page_config(page_title="评论自动打标工具", layout="wide")

st.title("📊 顾客评论自动打标系统")
st.markdown("""
**使用说明：**
1. 上传 Excel 文件。
2. **Sheet1**: 包含顾客评论和星级数据。
3. **Sheet2**: 好评标签库 | **Sheet3**: 差评标签库。
4. 系统会自动根据 1-3星(差评) 和 4-5星(好评) 的逻辑匹配标签。
""")

uploaded_file = st.file_uploader("请上传 Excel 文件 (.xlsx)", type=['xlsx'])

if uploaded_file is not None:
    with st.spinner('正在分析数据，请稍候...'):
        result_df, msg = process_data(uploaded_file)
        
        if result_df is not None:
            st.success("✅ 处理完成！预览前5行如下：")
            
            # 展示预览
            st.dataframe(result_df.head())
            
            # --- 转换为 CSV 供下载 ---
            # 使用 utf-8-sig 编码以防止 Excel 打开中文乱码
            csv = result_df.to_csv(index=False).encode('utf-8-sig')
            
            st.download_button(
                label="📥 下载 CSV 结果文件",
                data=csv,
                file_name='tagged_analysis_result.csv',
                mime='text/csv',
            )
        else:
            st.error(msg)