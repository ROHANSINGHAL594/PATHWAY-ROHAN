from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.tools import QuerySQLDataBaseTool
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from postgres_util import postgre_engine
from langchain_core.tools import tool
import asyncio

class TablePayload(BaseModel):
    table_name: str
    table_schema: Dict[str,Any]
    description: str

def build_schema_prompt(table_schema: Dict):
      prompt = "Table Schema:\n"
      for column, metadata in table_schema.items():
            dtype = metadata["dtype"]
            dtype_str = dtype if isinstance(dtype, str) else dtype["type"]
            pk_indicator = " [PRIMARY KEY]" if metadata["primary_key"] else ""
            prompt += f"  • {column}: {dtype_str}{pk_indicator}" 
            if metadata["description"] is not None:
                prompt += (f"- {metadata['description']}" )
            prompt += "\n"
      return prompt

def create_sql_tool(tables: List[TablePayload], agent_name: str):
            _db_instance: Optional[SQLDatabase] = None
            _sql_tool: Optional[QuerySQLDataBaseTool] = None
            table_descriptions = '\n'.join([
                f'{i+1}. {table.table_name}: {table.description}\n{build_schema_prompt(table.table_schema)}'
                for i, table in enumerate(tables)
            ])
            db_description = (
                f"SQL query tool. Read-only access to:\n\n"
                
                f"{table_descriptions}\n\n"
                
                "INPUT: Valid SQL SELECT statement\n"
                "OUTPUT: Query results (interpret these into natural language)\n\n"
                
                "USAGE TIPS:\n"
                "- Verify column names against schema before querying\n"
                "- Use WHERE clauses for filtering and postgres aggregation functions when aggregates are required/requested\n"
                "- Convert Unix timestamps to readable format\n"
                "- If query fails, analyze the error and retry with corrected SQL\n"
                "- Handling empty results on SELECT"
                "\t- If an SQL query returns empty results ([], empty string, or no rows), clearly state that no data was found\n"
                "\t- Explain what was searched for (e.g., 'No records found for X in table Y')\n"
                "\t- Do NOT make assumptions or provide placeholder data\n"
            )
            def lazy_init():
                nonlocal _db_instance, _sql_tool
                if _sql_tool is None:
                    _db_instance = SQLDatabase(
                        postgre_engine, 
                        include_tables=[table.table_name for table in tables]
                    )
                    
                    _sql_tool = QuerySQLDataBaseTool(db=_db_instance)
                return _sql_tool
            
            @tool("query_database", description=db_description)
            def query_db(query: str) -> str:
                sql_tool = lazy_init()
                raw_result = sql_tool.invoke(query)
                # The agent's LLM will see this raw result and convert it per the guidelines above
                return raw_result
            return query_db, table_descriptions