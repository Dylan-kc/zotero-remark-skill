                                                                      
# Zotero Remark                         
                                                                                                                      
  Claude Code Skill — 批量为 Zotero 文献添加简记                                                                      
                 
  根据文献摘要自动生成一句话总结，写入 Zotero 条目的 extra 字段中的 remark。                                          
                                                                                                                      
  ## 功能                                                                                                             
                                                                                                                      
  - 从指定文件夹批量提取 Zotero 文献                                                                                  
  - 读取每篇文献的摘要（abstractNote）                                                                                
  - 根据摘要内容生成一句话总结                                                                                        
  - 写入条目的"简记"（remark 字段）                                 
  - 支持分批处理（20 或 50 条），避免 API 频率限制
                                                                                                                      
  ## 适用场景
                                                                                                                      
  当你需要对大量 Zotero 文献进行整理时使用，例如：                  
  - "帮我处理 xxx 文件夹中的文献"        
  - "为这个文件夹的文献添加简记"
  - "根据摘要生成一句话总结"
                                                                                                                      
  ## 前置条件
                                                                                                                      
  1. 安装 pyzotero：`/opt/anaconda3/bin/python -m pip install pyzotero`
  2. 配置 Zotero API 凭证（创建 `.env` 文件）：
     ZOTERO_LIBRARY_ID=你的用户ID
     ZOTERO_API_KEY=你的API密钥                                                                                       
     ZOTERO_LIBRARY_TYPE=user
                                                                                                                      
  ## 使用方式                                                       
                                         
  在 Claude Code 中直接描述需求，Claude 会自动完成：                                                                  
  1. 连接 Zotero 账户
  2. 定位目标文件夹                                                                                                   
  3. 逐条读取摘要                                                   
  4. 生成一句话总结                      
  5. 写入 remark 字段

  ## Remark 格式                                                                                                      
  
  remark: 这里是一句话总结的内容                                                                                      
                                                                    
  存储在 Zotero 条目的 extra 字段中。    

  ## 技术要点

  - **API 分页**：Zotero API 每页 100 条，需要循环获取全部数据                                                        
  - **中英文处理**：无论原文语言，remark 均用中文生成
  - **Python 路径**：需使用 `/opt/anaconda3/bin/python`                                                               
                                                                                                                      
  ## License                             
                                                                                                                      
  MIT                                                               
       
