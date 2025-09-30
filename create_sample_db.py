# Create a sample SQLite database for testing
import sqlite3
import random
from datetime import datetime, timedelta

def create_sample_database():
    """Create a sample employee database for testing the NLP Query Engine."""
    
    # Create database connection
    conn = sqlite3.connect('sample_employee_database.db')
    cursor = conn.cursor()
    
    # Create departments table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        manager_id INTEGER,
        budget DECIMAL(12,2),
        location TEXT,
        created_date DATE
    )
    ''')
    
    # Create employees table  
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        email TEXT UNIQUE,
        phone TEXT,
        hire_date DATE,
        salary DECIMAL(10,2),
        department_id INTEGER,
        position TEXT,
        manager_id INTEGER,
        status TEXT DEFAULT 'active',
        FOREIGN KEY (department_id) REFERENCES departments (id),
        FOREIGN KEY (manager_id) REFERENCES employees (id)
    )
    ''')
    
    # Create projects table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        start_date DATE,
        end_date DATE,
        budget DECIMAL(12,2),
        status TEXT DEFAULT 'active',
        department_id INTEGER,
        FOREIGN KEY (department_id) REFERENCES departments (id)
    )
    ''')
    
    # Insert sample departments
    departments_data = [
        (1, 'Engineering', None, 1500000.00, 'Building A', '2020-01-01'),
        (2, 'Marketing', None, 800000.00, 'Building B', '2020-01-01'), 
        (3, 'Sales', None, 1200000.00, 'Building C', '2020-01-01'),
        (4, 'Human Resources', None, 600000.00, 'Building A', '2020-01-01'),
        (5, 'Finance', None, 900000.00, 'Building B', '2020-01-01')
    ]
    
    cursor.executemany('''
    INSERT OR REPLACE INTO departments (id, name, manager_id, budget, location, created_date)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', departments_data)
    
    # Insert sample employees
    employees_data = [
        # Engineering Department
        (1, 'John', 'Smith', 'john.smith@company.com', '555-0101', '2021-03-15', 95000.00, 1, 'Senior Software Engineer', None, 'active'),
        (2, 'Sarah', 'Johnson', 'sarah.johnson@company.com', '555-0102', '2022-01-10', 87000.00, 1, 'Software Engineer', 1, 'active'),
        (3, 'Mike', 'Davis', 'mike.davis@company.com', '555-0103', '2021-07-20', 92000.00, 1, 'DevOps Engineer', 1, 'active'),
        (4, 'Emily', 'Chen', 'emily.chen@company.com', '555-0104', '2023-02-01', 98000.00, 1, 'Senior Software Engineer', 1, 'active'),
        (5, 'David', 'Wilson', 'david.wilson@company.com', '555-0105', '2022-06-15', 85000.00, 1, 'Junior Software Engineer', 2, 'active'),
        
        # Marketing Department  
        (6, 'Lisa', 'Anderson', 'lisa.anderson@company.com', '555-0201', '2021-05-01', 75000.00, 2, 'Marketing Manager', None, 'active'),
        (7, 'James', 'Brown', 'james.brown@company.com', '555-0202', '2022-03-10', 65000.00, 2, 'Marketing Specialist', 6, 'active'),
        (8, 'Jennifer', 'Taylor', 'jennifer.taylor@company.com', '555-0203', '2021-11-15', 70000.00, 2, 'Content Manager', 6, 'active'),
        (9, 'Robert', 'Garcia', 'robert.garcia@company.com', '555-0204', '2024-01-15', 68000.00, 2, 'Digital Marketing Specialist', 6, 'active'),
        
        # Sales Department
        (10, 'Michelle', 'Martinez', 'michelle.martinez@company.com', '555-0301', '2020-08-01', 80000.00, 3, 'Sales Manager', None, 'active'),
        (11, 'Christopher', 'Lee', 'christopher.lee@company.com', '555-0302', '2021-12-01', 72000.00, 3, 'Senior Sales Rep', 10, 'active'),
        (12, 'Amanda', 'White', 'amanda.white@company.com', '555-0303', '2022-09-15', 68000.00, 3, 'Sales Representative', 10, 'active'),
        (13, 'Kevin', 'Thompson', 'kevin.thompson@company.com', '555-0304', '2023-04-01', 70000.00, 3, 'Sales Representative', 10, 'active'),
        
        # Human Resources
        (14, 'Maria', 'Rodriguez', 'maria.rodriguez@company.com', '555-0401', '2020-03-15', 78000.00, 4, 'HR Manager', None, 'active'),
        (15, 'Thomas', 'Jackson', 'thomas.jackson@company.com', '555-0402', '2021-08-20', 62000.00, 4, 'HR Specialist', 14, 'active'),
        
        # Finance
        (16, 'Nicole', 'Harris', 'nicole.harris@company.com', '555-0501', '2019-11-01', 85000.00, 5, 'Finance Manager', None, 'active'),
        (17, 'Daniel', 'Clark', 'daniel.clark@company.com', '555-0502', '2022-02-15', 71000.00, 5, 'Financial Analyst', 16, 'active'),
        (18, 'Laura', 'Lewis', 'laura.lewis@company.com', '555-0503', '2023-06-01', 73000.00, 5, 'Accountant', 16, 'active'),
        
        # Some inactive employees for testing
        (19, 'Mark', 'Walker', 'mark.walker@company.com', '555-0601', '2020-01-01', 90000.00, 1, 'Former Tech Lead', None, 'inactive'),
        (20, 'Jessica', 'Hall', 'jessica.hall@company.com', '555-0602', '2021-01-01', 67000.00, 2, 'Former Marketing Coord', None, 'inactive')
    ]
    
    cursor.executemany('''
    INSERT OR REPLACE INTO employees (id, first_name, last_name, email, phone, hire_date, salary, department_id, position, manager_id, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', employees_data)
    
    # Update manager_id for departments (set after employees are created)
    cursor.execute('UPDATE departments SET manager_id = 1 WHERE id = 1')  # John manages Engineering
    cursor.execute('UPDATE departments SET manager_id = 6 WHERE id = 2')  # Lisa manages Marketing  
    cursor.execute('UPDATE departments SET manager_id = 10 WHERE id = 3') # Michelle manages Sales
    cursor.execute('UPDATE departments SET manager_id = 14 WHERE id = 4') # Maria manages HR
    cursor.execute('UPDATE departments SET manager_id = 16 WHERE id = 5') # Nicole manages Finance
    
    # Insert sample projects
    projects_data = [
        (1, 'Customer Portal Redesign', 'Redesign the customer portal with modern UI/UX', '2023-01-15', '2023-06-30', 250000.00, 'completed', 1),
        (2, 'Mobile App Development', 'Develop native mobile application for iOS and Android', '2023-07-01', '2024-03-31', 400000.00, 'active', 1),
        (3, 'Digital Marketing Campaign Q1', 'Comprehensive digital marketing campaign for Q1 2024', '2024-01-01', '2024-03-31', 150000.00, 'completed', 2),
        (4, 'Brand Awareness Study', 'Market research study on brand awareness', '2024-02-01', '2024-05-31', 75000.00, 'active', 2),
        (5, 'Sales CRM Implementation', 'Implement new CRM system for sales team', '2023-09-01', '2024-01-31', 180000.00, 'completed', 3),
        (6, 'Employee Training Program', 'Develop comprehensive employee training program', '2024-01-15', '2024-08-31', 120000.00, 'active', 4),
        (7, 'Financial Systems Upgrade', 'Upgrade financial reporting and analysis systems', '2023-11-01', '2024-04-30', 200000.00, 'active', 5)
    ]
    
    cursor.executemany('''
    INSERT OR REPLACE INTO projects (id, name, description, start_date, end_date, budget, status, department_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', projects_data)
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print("✅ Sample database 'sample_employee_database.db' created successfully!")
    print("📊 Database contains:")
    print("   - 5 departments (Engineering, Marketing, Sales, HR, Finance)")
    print("   - 20 employees with realistic data")
    print("   - 7 projects across different departments")
    print("   - Foreign key relationships between tables")
    print("\n🎯 Try these sample queries:")
    print("   - 'How many employees are there?'")
    print("   - 'Show me employees in the Engineering department'") 
    print("   - 'What is the average salary?'")
    print("   - 'List the top 5 highest paid employees'")
    print("   - 'Show me all active projects'")
    print("   - 'How many employees were hired in 2023?'")

if __name__ == "__main__":
    create_sample_database()