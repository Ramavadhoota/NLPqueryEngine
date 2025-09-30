# backend/api/services/query_engine.py - Natural Language to SQL Query Engine

import logging
import sqlite3
import time
from typing import Dict, Any, List, Optional, Union
import re
from .schema_discovery import SQLiteSchemaDiscovery

logger = logging.getLogger(__name__)

class NaturalLanguageQueryEngine:
    """Convert natural language queries to SQL and execute them against SQLite."""
    
    def __init__(self, database_path: str):
        self.database_path = database_path
        self.connection = None
        self.schema_discovery = SQLiteSchemaDiscovery(database_path)
        self.schema_info = None
        
    def connect(self) -> bool:
        """Establish database connection."""
        try:
            if not self.schema_discovery.connect():
                return False
            
            self.connection = sqlite3.connect(self.database_path)
            self.connection.row_factory = sqlite3.Row
            
            # Cache schema information
            self.schema_info = self.schema_discovery.analyze_database()
            
            logger.info(f"✅ Query engine connected to database: {self.database_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect query engine: {e}")
            return False
    
    def disconnect(self):
        """Close database connections."""
        if self.connection:
            self.connection.close()
        if self.schema_discovery:
            self.schema_discovery.disconnect()
    
    async def execute_query(self, natural_query: str, include_documents: bool = True) -> Dict[str, Any]:
        """Execute natural language query against database and documents."""
        start_time = time.time()
        
        try:
            logger.info(f"🗣️ Processing natural language query: {natural_query}")
            
            # Map natural language to schema
            mapping = self.schema_discovery.map_natural_language_to_schema(
                natural_query, self.schema_info
            )
            
            # Generate SQL query
            sql_query = self._generate_sql_query(natural_query, mapping)
            
            # Execute SQL query
            database_results = []
            if sql_query:
                database_results = self._execute_sql_query(sql_query)
                logger.info(f"📊 SQL query returned {len(database_results)} rows")
            
            # Document search (placeholder for integration with DocumentProcessor)
            document_results = []
            if include_documents:
                document_results = self._search_documents(natural_query)
            
            execution_time = time.time() - start_time
            
            return {
                "sql_query": sql_query,
                "database_results": database_results,
                "document_results": document_results,
                "mapping": mapping,
                "execution_time": execution_time,
                "confidence": mapping.get("confidence", 0),
                "message": f"Query executed successfully in {execution_time:.2f}s"
            }
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            execution_time = time.time() - start_time
            return {
                "sql_query": None,
                "database_results": [],
                "document_results": [],
                "execution_time": execution_time,
                "confidence": 0,
                "message": f"Query execution failed: {str(e)}"
            }
    
    def _generate_sql_query(self, natural_query: str, mapping: Dict[str, Any]) -> Optional[str]:
        """Generate SQL query from natural language using schema mapping."""
        try:
            query_lower = natural_query.lower()
            query_type = mapping.get("query_type", "general")
            suggested_tables = mapping.get("suggested_tables", [])
            suggested_columns = mapping.get("suggested_columns", {})
            
            if not suggested_tables:
                logger.warning("No relevant tables found for query")
                return None
            
            # Get the most relevant table
            primary_table = suggested_tables[0]["table_name"]
            
            # Build SQL based on query type
            sql_parts = {
                "select": [],
                "from": primary_table,
                "joins": [],
                "where": [],
                "group_by": [],
                "order_by": [],
                "limit": None
            }
            
            # Generate SELECT clause based on query type
            if query_type == "count":
                sql_parts["select"] = ["COUNT(*) as count"]
            elif query_type == "aggregation":
                # Find numeric columns for aggregation
                numeric_cols = self._find_numeric_columns(primary_table, suggested_columns.get(primary_table, []))
                if numeric_cols:
                    if "average" in query_lower or "avg" in query_lower:
                        sql_parts["select"] = [f"AVG({numeric_cols[0]}) as average_{numeric_cols[0]}"]
                    else:
                        sql_parts["select"] = [f"AVG({numeric_cols[0]}) as average"]
                else:
                    sql_parts["select"] = ["COUNT(*) as count"]
            elif query_type == "sum":
                numeric_cols = self._find_numeric_columns(primary_table, suggested_columns.get(primary_table, []))
                if numeric_cols:
                    sql_parts["select"] = [f"SUM({numeric_cols[0]}) as total_{numeric_cols[0]}"]
                else:
                    sql_parts["select"] = ["*"]
            elif query_type == "ranking":
                # Select relevant columns and add ordering
                relevant_cols = self._get_relevant_columns(primary_table, suggested_columns.get(primary_table, []))
                sql_parts["select"] = relevant_cols if relevant_cols else ["*"]
                
                # Add ORDER BY for ranking
                if "highest" in query_lower or "max" in query_lower or "top" in query_lower:
                    numeric_cols = self._find_numeric_columns(primary_table, suggested_columns.get(primary_table, []))
                    if numeric_cols:
                        sql_parts["order_by"] = [f"{numeric_cols[0]} DESC"]
                elif "lowest" in query_lower or "min" in query_lower or "bottom" in query_lower:
                    numeric_cols = self._find_numeric_columns(primary_table, suggested_columns.get(primary_table, []))
                    if numeric_cols:
                        sql_parts["order_by"] = [f"{numeric_cols[0]} ASC"]
                
                # Add LIMIT for top/bottom queries
                if any(word in query_lower for word in ["top", "bottom"]):
                    # Try to extract number (e.g., "top 5", "bottom 10")
                    limit_match = re.search(r'(?:top|bottom)\s+(\d+)', query_lower)
                    if limit_match:
                        sql_parts["limit"] = int(limit_match.group(1))
                    else:
                        sql_parts["limit"] = 10  # Default limit
                        
            elif query_type == "grouping":
                # Group by relevant columns
                group_cols = self._find_grouping_columns(natural_query, primary_table, suggested_columns.get(primary_table, []))
                if group_cols:
                    sql_parts["select"] = group_cols + ["COUNT(*) as count"]
                    sql_parts["group_by"] = group_cols
                else:
                    sql_parts["select"] = ["*"]
            else:
                # General selection
                relevant_cols = self._get_relevant_columns(primary_table, suggested_columns.get(primary_table, []))
                sql_parts["select"] = relevant_cols if relevant_cols else ["*"]
            
            # Add WHERE conditions based on query content
            where_conditions = self._extract_where_conditions(natural_query, primary_table, suggested_columns.get(primary_table, []))
            sql_parts["where"] = where_conditions
            
            # Add JOINs if multiple tables are relevant
            if len(suggested_tables) > 1:
                joins = self._generate_joins(suggested_tables)
                sql_parts["joins"] = joins
            
            # Construct final SQL
            sql_query = self._build_sql_string(sql_parts)
            
            logger.info(f"🔧 Generated SQL: {sql_query}")
            return sql_query
            
        except Exception as e:
            logger.error(f"SQL generation failed: {e}")
            return None
    
    def _find_numeric_columns(self, table_name: str, columns: List[Dict]) -> List[str]:
        """Find numeric columns in the table for aggregation."""
        numeric_cols = []
        for col in columns:
            col_name = col["column_name"]
            data_type = col.get("data_type", "").lower()
            purpose = col.get("purpose", "").lower()
            
            if any(t in data_type for t in ["int", "numeric", "decimal", "float", "real"]) or purpose == "monetary":
                numeric_cols.append(col_name)
        
        return numeric_cols
    
    def _get_relevant_columns(self, table_name: str, columns: List[Dict]) -> List[str]:
        """Get most relevant columns for selection."""
        if not columns:
            return ["*"]
        
        # Sort by relevance and take top columns
        columns_sorted = sorted(columns, key=lambda x: x["relevance"], reverse=True)
        relevant_cols = [col["column_name"] for col in columns_sorted[:5]]  # Top 5 most relevant
        
        return relevant_cols if relevant_cols else ["*"]
    
    def _find_grouping_columns(self, query: str, table_name: str, columns: List[Dict]) -> List[str]:
        """Find columns suitable for GROUP BY based on query."""
        query_lower = query.lower()
        group_cols = []
        
        # Look for specific grouping patterns
        group_patterns = {
            "department": ["department", "dept", "division", "unit"],
            "role": ["role", "position", "title", "job"],
            "status": ["status", "state", "active"],
            "category": ["category", "type", "kind"],
            "location": ["location", "city", "state", "country"]
        }
        
        for group_type, synonyms in group_patterns.items():
            if any(synonym in query_lower for synonym in synonyms):
                # Find matching columns
                for col in columns:
                    col_name = col["column_name"].lower()
                    if any(synonym in col_name for synonym in synonyms):
                        group_cols.append(col["column_name"])
                        break
        
        return group_cols
    
    def _extract_where_conditions(self, query: str, table_name: str, columns: List[Dict]) -> List[str]:
        """Extract WHERE conditions from natural language."""
        conditions = []
        query_lower = query.lower()
        
        # Date-based conditions
        year_match = re.search(r'(20\d{2})', query)
        if year_match:
            year = year_match.group(1)
            # Find date columns
            date_cols = [col["column_name"] for col in columns if "date" in col.get("purpose", "").lower()]
            if date_cols:
                conditions.append(f"strftime('%Y', {date_cols[0]}) = '{year}'")
        
        # Status conditions
        if "active" in query_lower:
            status_cols = [col["column_name"] for col in columns if "status" in col["column_name"].lower()]
            if status_cols:
                conditions.append(f"{status_cols[0]} = 'active'")
        
        # Numeric conditions  
        salary_match = re.search(r'salary[\s><=]+([,\d]+)', query_lower)
        if salary_match:
            amount = salary_match.group(1).replace(',', '')
            salary_cols = [col["column_name"] for col in columns if "salary" in col["column_name"].lower()]
            if salary_cols:
                if ">" in query_lower or "above" in query_lower or "more than" in query_lower:
                    conditions.append(f"{salary_cols[0]} > {amount}")
                elif "<" in query_lower or "below" in query_lower or "less than" in query_lower:
                    conditions.append(f"{salary_cols[0]} < {amount}")
        
        return conditions
    
    def _generate_joins(self, tables: List[Dict]) -> List[str]:
        """Generate JOIN clauses for multiple tables."""
        joins = []
        # This is simplified - in production, you'd analyze foreign key relationships
        primary_table = tables[0]["table_name"]
        
        for i in range(1, len(tables)):
            secondary_table = tables[i]["table_name"]
            
            # Look for common join patterns
            if "department" in secondary_table.lower() and "employee" in primary_table.lower():
                joins.append(f"LEFT JOIN {secondary_table} ON {primary_table}.department_id = {secondary_table}.id")
            elif "employee" in secondary_table.lower() and "department" in primary_table.lower():
                joins.append(f"LEFT JOIN {secondary_table} ON {primary_table}.id = {secondary_table}.department_id")
        
        return joins
    
    def _build_sql_string(self, sql_parts: Dict[str, Any]) -> str:
        """Build final SQL string from parts."""
        sql = f"SELECT {', '.join(sql_parts['select'])}"
        sql += f" FROM {sql_parts['from']}"
        
        if sql_parts["joins"]:
            sql += " " + " ".join(sql_parts["joins"])
        
        if sql_parts["where"]:
            sql += f" WHERE {' AND '.join(sql_parts['where'])}"
        
        if sql_parts["group_by"]:
            sql += f" GROUP BY {', '.join(sql_parts['group_by'])}"
        
        if sql_parts["order_by"]:
            sql += f" ORDER BY {', '.join(sql_parts['order_by'])}"
        
        if sql_parts["limit"]:
            sql += f" LIMIT {sql_parts['limit']}"
        
        return sql
    
    def _execute_sql_query(self, sql_query: str) -> List[Dict[str, Any]]:
        """Execute SQL query and return results."""
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql_query)
            
            # Get column names
            columns = [description[0] for description in cursor.description]
            
            # Fetch results
            rows = cursor.fetchall()
            
            # Convert to list of dictionaries
            results = []
            for row in rows:
                result_dict = {}
                for i, value in enumerate(row):
                    result_dict[columns[i]] = value
                results.append(result_dict)
            
            return results
            
        except Exception as e:
            logger.error(f"SQL execution failed: {e}")
            raise
    
    def _search_documents(self, query: str) -> List[Dict]:
        """Search documents (integration point for DocumentProcessor)."""
        # This would integrate with the DocumentProcessor in a full implementation
        # For now, return empty list
        return []
    
    async def explain_query(self, natural_query: str) -> Dict[str, Any]:
        """Explain how the natural language query will be processed."""
        try:
            mapping = self.schema_discovery.map_natural_language_to_schema(
                natural_query, self.schema_info
            )
            
            sql_query = self._generate_sql_query(natural_query, mapping)
            
            explanation = {
                "original_query": natural_query,
                "query_type": mapping.get("query_type"),
                "confidence": mapping.get("confidence"),
                "suggested_tables": mapping.get("suggested_tables"),
                "suggested_columns": mapping.get("suggested_columns"),
                "generated_sql": sql_query,
                "sql_hints": mapping.get("sql_hints", []),
                "explanation_text": self._generate_explanation_text(natural_query, mapping, sql_query)
            }
            
            return explanation
            
        except Exception as e:
            logger.error(f"Query explanation failed: {e}")
            raise
    
    def _generate_explanation_text(self, query: str, mapping: Dict, sql: str) -> str:
        """Generate human-readable explanation of query processing."""
        explanation = f"I interpreted your query '{query}' as a {mapping.get('query_type', 'general')} operation. "
        
        suggested_tables = mapping.get("suggested_tables", [])
        if suggested_tables:
            table_names = [t["table_name"] for t in suggested_tables[:2]]
            explanation += f"I found these relevant tables: {', '.join(table_names)}. "
        
        if sql:
            explanation += f"This was converted to the SQL query: {sql}"
        else:
            explanation += "I couldn't generate a suitable SQL query for this request."
        
        confidence = mapping.get("confidence", 0)
        explanation += f" Confidence level: {confidence:.1%}"
        
        return explanation
    
    async def generate_query_suggestions(self) -> List[Dict[str, str]]:
        """Generate sample queries based on database schema."""
        suggestions = []
        
        if not self.schema_info:
            return suggestions
        
        tables = self.schema_info.get("tables", {})
        
        for table_name, table_info in tables.items():
            purpose = table_info.get("purpose", "unknown")
            
            if purpose == "employees":
                suggestions.extend([
                    {"query": f"How many employees are there?", "category": "Count"},
                    {"query": f"Show all employees hired in 2024", "category": "Filter"},
                    {"query": f"List employees by department", "category": "Group"},
                ])
            elif purpose == "departments":
                suggestions.extend([
                    {"query": f"List all departments", "category": "List"},
                    {"query": f"Show departments with more than 10 employees", "category": "Filter"}
                ])
            elif purpose == "compensation":
                suggestions.extend([
                    {"query": f"What is the average salary?", "category": "Aggregation"},
                    {"query": f"Show top 5 highest paid employees", "category": "Ranking"}
                ])
        
        # Add generic suggestions
        suggestions.extend([
            {"query": "Show me recent data", "category": "Recent"},
            {"query": "Find records with high values", "category": "Filter"},
            {"query": "Group data by categories", "category": "Group"}
        ])
        
        return suggestions[:10]  # Return top 10 suggestions