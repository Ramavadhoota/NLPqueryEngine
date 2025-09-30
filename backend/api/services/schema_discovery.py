# backend/api/services/schema_discovery.py - SQLite Schema Discovery Service

import sqlite3
import logging
from typing import Dict, List, Any, Optional, Union
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)

class SQLiteSchemaDiscovery:
    """SQLite-specific schema discovery and analysis for NLP Query Engine."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection = None
        
    def connect(self) -> bool:
        """Establish database connection."""
        try:
            # Check if database file exists
            if not os.path.exists(self.db_path):
                logger.error(f"Database file not found: {self.db_path}")
                return False
                
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row  # Enable column access by name
            logger.info(f"Connected to SQLite database: {self.db_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False
    
    def disconnect(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def analyze_database(self) -> Dict[str, Any]:
        """Automatically discover SQLite database schema - NO HARD-CODING."""
        if not self.connection:
            raise ValueError("Database connection not established")
        
        try:
            cursor = self.connection.cursor()
            schema_info = {
                "tables": {},
                "relationships": {},
                "statistics": {},
                "naming_patterns": {},
                "database_type": "sqlite"
            }
            
            # Get all table names (exclude SQLite system tables)
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            tables = [row[0] for row in cursor.fetchall()]
            logger.info(f"🔍 Found {len(tables)} tables: {tables}")
            
            for table_name in tables:
                # Analyze each table structure and content
                table_info = self._analyze_table(table_name, cursor)
                schema_info["tables"][table_name] = table_info
                
                # Automatically detect table purpose (employees, departments, etc.)
                purpose = self._detect_table_purpose(table_name, table_info)
                schema_info["tables"][table_name]["purpose"] = purpose
            
            # Analyze relationships between tables
            schema_info["relationships"] = self._analyze_relationships(tables, cursor)
            
            # Generate naming pattern mappings for natural language
            schema_info["naming_patterns"] = self._analyze_naming_patterns(schema_info["tables"])
            
            # Collect database statistics
            schema_info["statistics"] = self._collect_statistics(tables, cursor)
            
            logger.info(f"✅ Schema analysis complete: {len(tables)} tables analyzed")
            return schema_info
            
        except Exception as e:
            logger.error(f"Schema analysis failed: {e}")
            raise
    
    def _analyze_table(self, table_name: str, cursor) -> Dict[str, Any]:
        """Analyze individual table structure and sample data."""
        try:
            # Get column information using SQLite PRAGMA
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = []
            primary_keys = []
            
            for row in cursor.fetchall():
                col_info = {
                    "name": row[1],
                    "type": row[2],
                    "not_null": bool(row[3]),
                    "default_value": row[4],
                    "primary_key": bool(row[5])
                }
                columns.append(col_info)
                if col_info["primary_key"]:
                    primary_keys.append(col_info["name"])
            
            # Get foreign key information
            cursor.execute(f"PRAGMA foreign_key_list({table_name})")
            foreign_keys = []
            for row in cursor.fetchall():
                foreign_keys.append({
                    "column": row[3],
                    "referenced_table": row[2],
                    "referenced_column": row[4]
                })
            
            # Get sample data (limit to 3 rows for efficiency)
            try:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                sample_rows = []
                for row in cursor.fetchall():
                    # Convert sqlite3.Row to dict
                    sample_rows.append({col: row[i] for i, col in enumerate([col[0] for col in cursor.description])})
            except Exception as e:
                logger.warning(f"Could not fetch sample data from {table_name}: {e}")
                sample_rows = []
            
            # Get row count
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cursor.fetchone()[0]
            except Exception as e:
                logger.warning(f"Could not get row count for {table_name}: {e}")
                row_count = 0
            
            # Detect column purposes based on names and types
            column_purposes = {}
            for col in columns:
                purpose = self._detect_column_purpose(col["name"], col["type"])
                column_purposes[col["name"]] = purpose
            
            return {
                "columns": columns,
                "primary_keys": primary_keys,
                "foreign_keys": foreign_keys,
                "sample_data": sample_rows,
                "row_count": row_count,
                "column_purposes": column_purposes
            }
            
        except Exception as e:
            logger.error(f"Table analysis failed for {table_name}: {e}")
            return {
                "columns": [],
                "primary_keys": [],
                "foreign_keys": [],
                "sample_data": [],
                "row_count": 0,
                "column_purposes": {}
            }
    
    def _detect_table_purpose(self, table_name: str, table_info: Dict) -> str:
        """Automatically detect table purpose - NO HARD-CODING."""
        name_lower = table_name.lower()
        
        # Employee-related patterns
        employee_keywords = ["employee", "emp", "staff", "personnel", "worker", "user", "person"]
        if any(keyword in name_lower for keyword in employee_keywords):
            return "employees"
        
        # Department-related patterns  
        dept_keywords = ["department", "dept", "division", "unit", "team", "group"]
        if any(keyword in name_lower for keyword in dept_keywords):
            return "departments"
            
        # Salary/compensation patterns
        salary_keywords = ["salary", "compensation", "pay", "wage", "payroll", "earning"]
        if any(keyword in name_lower for keyword in salary_keywords):
            return "compensation"
            
        # Project patterns
        project_keywords = ["project", "assignment", "task", "work", "job"]
        if any(keyword in name_lower for keyword in project_keywords):
            return "projects"
            
        # Role/position patterns
        role_keywords = ["role", "position", "job", "title", "designation"]
        if any(keyword in name_lower for keyword in role_keywords):
            return "roles"
            
        # Document patterns
        doc_keywords = ["document", "doc", "file", "attachment", "record"]
        if any(keyword in name_lower for keyword in doc_keywords):
            return "documents"
            
        # Generic data patterns
        if any(keyword in name_lower for keyword in ["order", "purchase", "sale", "transaction"]):
            return "transactions"
        if any(keyword in name_lower for keyword in ["product", "item", "inventory", "stock"]):
            return "products"
        if any(keyword in name_lower for keyword in ["customer", "client", "contact"]):
            return "customers"
            
        return "unknown"
    
    def _detect_column_purpose(self, column_name: str, column_type: str) -> str:
        """Automatically detect column purpose from name and type."""
        name_lower = column_name.lower()
        type_str = str(column_type).lower()
        
        # Identifier patterns
        if any(keyword in name_lower for keyword in ["id", "key"]) or name_lower.endswith("_id"):
            return "identifier"
            
        # Name patterns
        if any(keyword in name_lower for keyword in ["name", "title", "label", "fname", "lname", "first_name", "last_name"]):
            return "name"
            
        # Contact information
        if any(keyword in name_lower for keyword in ["email", "mail", "e_mail"]):
            return "email"
        if any(keyword in name_lower for keyword in ["phone", "tel", "mobile", "contact"]):
            return "phone"
            
        # Date/time patterns
        if any(keyword in name_lower for keyword in ["date", "time", "created", "updated", "modified", "timestamp"]):
            return "datetime"
            
        # Financial patterns
        if any(keyword in name_lower for keyword in ["salary", "wage", "pay", "compensation", "amount", "price", "cost"]):
            return "monetary"
            
        # Location patterns  
        if any(keyword in name_lower for keyword in ["address", "location", "city", "state", "country", "zip", "postal"]):
            return "location"
            
        # Status/category patterns
        if any(keyword in name_lower for keyword in ["status", "state", "category", "type", "kind"]):
            return "category"
            
        # Based on data type
        if any(t in type_str for t in ["varchar", "text", "char", "string"]):
            return "text"
        if any(t in type_str for t in ["int", "integer", "numeric", "decimal", "float", "real", "double"]):
            return "numeric"
        if any(t in type_str for t in ["date", "time", "timestamp", "datetime"]):
            return "datetime"
        if any(t in type_str for t in ["bool", "boolean"]):
            return "boolean"
            
        return "unknown"
    
    def _analyze_relationships(self, table_names: List[str], cursor) -> Dict[str, List[Dict]]:
        """Analyze foreign key relationships between tables."""
        relationships = {}
        
        for table_name in table_names:
            try:
                cursor.execute(f"PRAGMA foreign_key_list({table_name})")
                table_relationships = []
                
                for row in cursor.fetchall():
                    relationship = {
                        "type": "foreign_key",
                        "local_column": row[3],
                        "remote_table": row[2],
                        "remote_column": row[4],
                        "relationship_strength": "strong"
                    }
                    table_relationships.append(relationship)
                
                relationships[table_name] = table_relationships
            except Exception as e:
                logger.warning(f"Could not analyze relationships for {table_name}: {e}")
                relationships[table_name] = []
        
        return relationships
    
    def _analyze_naming_patterns(self, tables: Dict) -> Dict[str, Dict]:
        """Create naming pattern mappings for natural language queries."""
        patterns = {
            "column_synonyms": {
                # Employee field synonyms
                "employee_id": ["emp_id", "staff_id", "worker_id", "personnel_id", "user_id"],
                "first_name": ["fname", "given_name", "forename", "name"],
                "last_name": ["lname", "surname", "family_name"],
                "full_name": ["name", "employee_name", "person_name"],
                "salary": ["wage", "pay", "compensation", "income", "earnings"],
                "department": ["dept", "division", "unit", "section", "team"],
                "hire_date": ["start_date", "join_date", "employment_date", "hired"],
                "email": ["email_address", "mail", "e_mail", "contact_email"],
                "phone": ["phone_number", "telephone", "mobile", "contact_number"],
                "address": ["location", "street_address", "home_address"],
                "position": ["job_title", "role", "designation", "title"],
                "manager": ["supervisor", "boss", "lead", "manager_id"],
                "status": ["state", "condition", "active", "inactive"]
            },
            "table_synonyms": {
                "employees": ["employee", "emp", "staff", "personnel", "worker", "people"],
                "departments": ["department", "dept", "division", "unit", "team"],
                "salaries": ["salary", "compensation", "pay", "wage", "payroll"],
                "projects": ["project", "assignment", "task", "work"],
                "orders": ["order", "purchase", "sale", "transaction"],
                "customers": ["customer", "client", "contact", "user"],
                "products": ["product", "item", "inventory", "stock"]
            },
            "query_patterns": {
                "count": ["how many", "number of", "count of", "total"],
                "average": ["average", "avg", "mean"],
                "maximum": ["highest", "max", "maximum", "top", "largest"],
                "minimum": ["lowest", "min", "minimum", "bottom", "smallest"],
                "list": ["show", "display", "list", "get", "find", "all"],
                "filter": ["where", "with", "having", "that have"],
                "group": ["by department", "by role", "group by", "grouped by"]
            }
        }
        
        return patterns
    
    def _collect_statistics(self, table_names: List[str], cursor) -> Dict[str, Any]:
        """Collect database usage statistics."""
        stats = {
            "total_tables": len(table_names),
            "total_rows": 0,
            "table_sizes": {},
            "database_size_mb": 0
        }
        
        # Calculate total rows and table sizes
        for table_name in table_names:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cursor.fetchone()[0]
                stats["total_rows"] += row_count
                stats["table_sizes"][table_name] = row_count
            except Exception as e:
                logger.warning(f"Could not get statistics for {table_name}: {e}")
                stats["table_sizes"][table_name] = 0
        
        # Get database file size
        try:
            db_size_bytes = os.path.getsize(self.db_path)
            stats["database_size_mb"] = round(db_size_bytes / (1024 * 1024), 2)
        except Exception as e:
            logger.warning(f"Could not get database file size: {e}")
        
        return stats
    
    def map_natural_language_to_schema(self, query: str, schema_info: Dict) -> Dict[str, Any]:
        """Map natural language terms to actual database schema - CORE FEATURE."""
        mapping = {
            "suggested_tables": [],
            "suggested_columns": {},
            "query_type": self._classify_query_type(query),
            "confidence": 0.0,
            "sql_hints": []
        }
        
        query_lower = query.lower()
        tables = schema_info.get("tables", {})
        patterns = schema_info.get("naming_patterns", {})
        
        # Find relevant tables based on query content
        for table_name, table_info in tables.items():
            relevance = self._calculate_table_relevance(query_lower, table_name, table_info, patterns)
            if relevance > 0.2:  # Threshold for relevance
                mapping["suggested_tables"].append({
                    "table_name": table_name,
                    "relevance": relevance,
                    "purpose": table_info.get("purpose", "unknown")
                })
        
        # Sort tables by relevance
        mapping["suggested_tables"].sort(key=lambda x: x["relevance"], reverse=True)
        
        # Find relevant columns for each suggested table
        for table_info in mapping["suggested_tables"]:
            table_name = table_info["table_name"]
            table_data = tables[table_name]
            
            relevant_columns = []
            for col_info in table_data.get("columns", []):
                col_name = col_info["name"]
                col_relevance = self._calculate_column_relevance(query_lower, col_name, col_info, patterns)
                if col_relevance > 0.1:
                    relevant_columns.append({
                        "column_name": col_name,
                        "relevance": col_relevance,
                        "purpose": table_data.get("column_purposes", {}).get(col_name, "unknown"),
                        "data_type": col_info.get("type", "unknown")
                    })
            
            # Sort columns by relevance
            relevant_columns.sort(key=lambda x: x["relevance"], reverse=True)
            mapping["suggested_columns"][table_name] = relevant_columns
        
        # Generate SQL hints based on query type and content
        mapping["sql_hints"] = self._generate_sql_hints(query_lower, mapping)
        
        # Calculate overall confidence
        mapping["confidence"] = self._calculate_mapping_confidence(mapping)
        
        return mapping
    
    def _classify_query_type(self, query: str) -> str:
        """Classify the type of query based on natural language."""
        query_lower = query.lower()
        
        if any(keyword in query_lower for keyword in ["count", "how many", "number of", "total"]):
            return "count"
        elif any(keyword in query_lower for keyword in ["average", "avg", "mean"]):
            return "aggregation"
        elif any(keyword in query_lower for keyword in ["highest", "lowest", "top", "bottom", "max", "min"]):
            return "ranking"
        elif any(keyword in query_lower for keyword in ["sum", "total amount", "sum of"]):
            return "sum"
        elif any(keyword in query_lower for keyword in ["group by", "by department", "by role", "grouped by"]):
            return "grouping"
        elif any(keyword in query_lower for keyword in ["list", "show", "display", "get", "find", "all"]):
            return "selection"
        else:
            return "general"
    
    def _calculate_table_relevance(self, query: str, table_name: str, table_info: Dict, patterns: Dict) -> float:
        """Calculate how relevant a table is to the natural language query."""
        relevance = 0.0
        
        # Direct table name match
        if table_name.lower() in query:
            relevance += 0.8
        
        # Check table synonyms
        table_synonyms = patterns.get("table_synonyms", {})
        for canonical_name, synonyms in table_synonyms.items():
            if table_name.lower() in synonyms:
                for synonym in synonyms:
                    if synonym in query:
                        relevance += 0.7
                        break
        
        # Purpose-based matching
        purpose = table_info.get("purpose", "")
        if purpose in query:
            relevance += 0.6
        
        # Column name matches (indicates table relevance)
        columns = table_info.get("columns", [])
        column_matches = 0
        for col in columns:
            if col["name"].lower() in query:
                column_matches += 1
                relevance += 0.2
        
        # Bonus for multiple column matches
        if column_matches > 2:
            relevance += 0.3
        
        return min(relevance, 1.0)
    
    def _calculate_column_relevance(self, query: str, column_name: str, column_info: Dict, patterns: Dict) -> float:
        """Calculate how relevant a column is to the natural language query."""
        relevance = 0.0
        
        # Direct column name match
        if column_name.lower() in query:
            relevance += 0.8
        
        # Check column synonyms
        column_synonyms = patterns.get("column_synonyms", {})
        for canonical_name, synonyms in column_synonyms.items():
            if column_name.lower() in synonyms or column_name.lower() == canonical_name:
                for synonym in synonyms:
                    if synonym in query:
                        relevance += 0.7
                        break
        
        # Purpose-based matching
        purpose = column_info.get("purpose", "")
        if purpose in query:
            relevance += 0.5
        
        # Data type relevance
        if "salary" in query and column_info.get("type", "").lower() in ["decimal", "numeric", "integer"]:
            relevance += 0.3
        if "name" in query and column_info.get("type", "").lower() in ["varchar", "text", "char"]:
            relevance += 0.3
        if "date" in query and "date" in column_info.get("type", "").lower():
            relevance += 0.3
        
        return min(relevance, 1.0)
    
    def _generate_sql_hints(self, query: str, mapping: Dict) -> List[str]:
        """Generate SQL construction hints based on query analysis."""
        hints = []
        query_type = mapping["query_type"]
        
        if query_type == "count":
            hints.append("Use SELECT COUNT(*) or COUNT(column_name)")
        elif query_type == "aggregation":
            hints.append("Use AVG() function")
        elif query_type == "ranking":
            hints.append("Use ORDER BY with LIMIT")
        elif query_type == "sum":
            hints.append("Use SUM() function")
        elif query_type == "grouping":
            hints.append("Use GROUP BY clause")
        elif query_type == "selection":
            hints.append("Use SELECT with WHERE conditions")
        
        # Add JOIN hints if multiple tables are relevant
        if len(mapping["suggested_tables"]) > 1:
            hints.append("Consider JOINing tables using foreign key relationships")
        
        return hints
    
    def _calculate_mapping_confidence(self, mapping: Dict) -> float:
        """Calculate overall confidence of the natural language mapping."""
        if not mapping["suggested_tables"]:
            return 0.0
        
        # Factor in table relevance
        table_relevances = [t["relevance"] for t in mapping["suggested_tables"]]
        avg_table_relevance = sum(table_relevances) / len(table_relevances)
        
        # Factor in column coverage
        tables_with_columns = len([cols for cols in mapping["suggested_columns"].values() if cols])
        total_suggested_tables = len(mapping["suggested_tables"])
        
        if total_suggested_tables == 0:
            column_coverage = 0
        else:
            column_coverage = tables_with_columns / total_suggested_tables
        
        # Query type confidence
        query_type_confidence = 0.8 if mapping["query_type"] != "general" else 0.4
        
        # Combine factors
        confidence = (avg_table_relevance * 0.4 + column_coverage * 0.3 + query_type_confidence * 0.3)
        return min(confidence, 1.0)