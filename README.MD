# Notes
## Update Audits
1. Directly use LLM for finding tasks actually very accurate and fast, even for 100 items, altough the concern of scalability and efficiency still remains. Therefore the use of embeddings is introduced in this version of implementation. 
2. `all-MiniLM-L6-v2` model is not accurate for finding revelant texts, swithed to `all-mpnet-base-v2`. 
3. Introduce LLM enhancement prompt for task description (and query) in order to improve matching. `EnhancedVectorIndex` 

## Exeuction
1. Set the enviornment variable for Google API Key in Windows Power Shell by: 
    ```
    $env:GOOGLE_API_KEY = "your_api_key_here"
    echo $env:GOOGLE_API_KEY
    ```
2. Run Streamkit
    ```
    streamlit run todo.rag.main.py
    ```


## Archtiecture
```mermaid
architecture-beta
    
    service db_s(database)[SQL]
    service db_s_man(server)[Persistence SQL]
	service db_v(database)[Vector]
	service db_v_man(server)[Persistence Vector]
    service db_man(server)[Persistence]
    service embedding(internet)[Embedding]
	service business(server)[Service]
    service cache(server)[Cache]
    service rag(server)[RAG]
    service llm(internet)[LLM]
    service ui(internet)[Web]

    ui:R -- L:business
	business:R -- L:db_man
	business:T -- B:rag
	rag:T -- B:llm
	business:B -- T:cache
	db_man:T -- B:db_v_man
	db_v_man:R -- L:embedding
	db_v_man:T -- B:db_v
	db_man:B -- T:db_s_man
	db_s_man:B -- T:db_s		

```
[PNG](doc/img/llm.todo.architecture.png)