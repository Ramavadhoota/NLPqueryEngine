// frontend/app.js - Main JavaScript Application

class NLPQueryEngine {
    constructor() {
        this.apiBaseUrl = 'http://localhost:8000/api/v1';
        this.databasePath = null;
        this.isConnected = false;
        this.schemaInfo = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupDragAndDrop();
        this.setupTabSwitching();
        console.log('🚀 NLP Query Engine initialized');
    }

    setupEventListeners() {
        // Database connection
        const databaseFile = document.getElementById('databaseFile');
        const connectButton = document.getElementById('connectButton');
        const databaseUploadArea = document.getElementById('databaseUploadArea');

        databaseUploadArea.addEventListener('click', () => databaseFile.click());
        databaseFile.addEventListener('change', this.handleDatabaseFileSelect.bind(this));
        connectButton.addEventListener('click', this.connectToDatabase.bind(this));

        // Document upload
        const documentsFile = document.getElementById('documentsFile');
        const uploadDocumentsButton = document.getElementById('uploadDocumentsButton');
        const documentsUploadArea = document.getElementById('documentsUploadArea');

        documentsUploadArea.addEventListener('click', () => documentsFile.click());
        documentsFile.addEventListener('change', this.handleDocumentsFileSelect.bind(this));
        uploadDocumentsButton.addEventListener('click', this.uploadDocuments.bind(this));

        // Query execution
        const queryInput = document.getElementById('queryInput');
        const executeQueryButton = document.getElementById('executeQueryButton');
        const explainQueryButton = document.getElementById('explainQueryButton');
        const suggestionsButton = document.getElementById('suggestionsButton');

        executeQueryButton.addEventListener('click', this.executeQuery.bind(this));
        explainQueryButton.addEventListener('click', this.explainQuery.bind(this));
        suggestionsButton.addEventListener('click', this.getQuerySuggestions.bind(this));

        // Enable query execution on Enter
        queryInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                this.executeQuery();
            }
        });

        // Enable buttons when query is entered
        queryInput.addEventListener('input', () => {
            const hasQuery = queryInput.value.trim().length > 0;
            const canQuery = this.isConnected && hasQuery;
            
            executeQueryButton.disabled = !canQuery;
            explainQueryButton.disabled = !canQuery;
            suggestionsButton.disabled = !this.isConnected;
        });
    }

    setupDragAndDrop() {
        // Database file drag and drop
        const databaseUploadArea = document.getElementById('databaseUploadArea');
        const databaseFile = document.getElementById('databaseFile');

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            databaseUploadArea.addEventListener(eventName, this.preventDefaults, false);
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            databaseUploadArea.addEventListener(eventName, () => {
                databaseUploadArea.classList.add('dragover');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            databaseUploadArea.addEventListener(eventName, () => {
                databaseUploadArea.classList.remove('dragover');
            }, false);
        });

        databaseUploadArea.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                databaseFile.files = files;
                this.handleDatabaseFileSelect({ target: { files } });
            }
        }, false);

        // Documents drag and drop
        const documentsUploadArea = document.getElementById('documentsUploadArea');
        const documentsFile = document.getElementById('documentsFile');

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            documentsUploadArea.addEventListener(eventName, this.preventDefaults, false);
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            documentsUploadArea.addEventListener(eventName, () => {
                documentsUploadArea.classList.add('dragover');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            documentsUploadArea.addEventListener(eventName, () => {
                documentsUploadArea.classList.remove('dragover');
            }, false);
        });

        documentsUploadArea.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                documentsFile.files = files;
                this.handleDocumentsFileSelect({ target: { files } });
            }
        }, false);
    }

    setupTabSwitching() {
        const tabButtons = document.querySelectorAll('.tab-button');
        const tabContents = document.querySelectorAll('.tab-content');

        tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                const targetTab = button.getAttribute('data-tab');
                
                // Update active tab button
                tabButtons.forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');
                
                // Update active tab content
                tabContents.forEach(content => {
                    content.classList.remove('active');
                    if (content.id === targetTab + 'Results') {
                        content.classList.add('active');
                    }
                });
            });
        });
    }

    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    showLoading(message = 'Processing...') {
        const overlay = document.getElementById('loadingOverlay');
        const loadingMessage = document.getElementById('loadingMessage');
        loadingMessage.textContent = message;
        overlay.classList.remove('hidden');
    }

    hideLoading() {
        const overlay = document.getElementById('loadingOverlay');
        overlay.classList.add('hidden');
    }

    showNotification(message, type = 'info') {
        // Simple notification system
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        Object.assign(notification.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            padding: '1rem 1.5rem',
            borderRadius: '0.5rem',
            color: 'white',
            fontWeight: '500',
            zIndex: '1001',
            transform: 'translateX(100%)',
            transition: 'transform 0.3s ease-in-out'
        });

        if (type === 'success') {
            notification.style.background = 'var(--success-color)';
        } else if (type === 'error') {
            notification.style.background = 'var(--error-color)';
        } else {
            notification.style.background = 'var(--primary-color)';
        }

        document.body.appendChild(notification);

        // Animate in
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 100);

        // Remove after delay
        setTimeout(() => {
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 3000);
    }

    updateConnectionStatus(status, message) {
        const statusElement = document.getElementById('connectionStatus');
        const icon = statusElement.querySelector('i');
        const text = statusElement.querySelector('span');

        statusElement.className = `connection-status ${status}`;
        text.textContent = message;

        if (status === 'connected') {
            icon.className = 'fas fa-check-circle';
            this.isConnected = true;
        } else if (status === 'connecting') {
            icon.className = 'fas fa-spinner fa-spin';
            this.isConnected = false;
        } else {
            icon.className = 'fas fa-times-circle';
            this.isConnected = false;
        }
    }

    handleDatabaseFileSelect(event) {
        const file = event.target.files[0];
        if (file) {
            console.log('📁 Database file selected:', file.name);
            document.getElementById('connectButton').disabled = false;
            
            // Update upload area text
            const uploadArea = document.getElementById('databaseUploadArea');
            const content = uploadArea.querySelector('.upload-content');
            content.innerHTML = `
                <i class="fas fa-check-circle" style="color: var(--success-color);"></i>
                <p><strong>${file.name}</strong> selected</p>
                <small>Ready to connect and analyze</small>
            `;
        }
    }

    handleDocumentsFileSelect(event) {
        const files = Array.from(event.target.files);
        if (files.length > 0) {
            console.log('📄 Documents selected:', files.length);
            document.getElementById('uploadDocumentsButton').disabled = false;
            
            // Update upload area text
            const uploadArea = document.getElementById('documentsUploadArea');
            const content = uploadArea.querySelector('.upload-content');
            content.innerHTML = `
                <i class="fas fa-check-circle" style="color: var(--success-color);"></i>
                <p><strong>${files.length} document(s)</strong> selected</p>
                <small>Ready to process with all-MiniLM-L6-v2</small>
            `;
        }
    }

    async connectToDatabase() {
        const fileInput = document.getElementById('databaseFile');
        const file = fileInput.files[0];
        
        if (!file) {
            this.showNotification('Please select a database file', 'error');
            return;
        }

        this.showLoading('🔍 Analyzing database schema...');
        this.updateConnectionStatus('connecting', 'Analyzing...');

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch(`${this.apiBaseUrl}/schema/upload-db`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                this.databasePath = result.temp_path;
                this.schemaInfo = result.schema_info;
                
                this.updateConnectionStatus('connected', `Connected to ${result.filename}`);
                this.displaySchemaInfo(result.schema_info);
                this.showNotification(`Database connected! Found ${Object.keys(result.schema_info.tables).length} tables`, 'success');
                
                // Enable query interface
                document.getElementById('suggestionsButton').disabled = false;
                
                console.log('✅ Database connected:', result);
            } else {
                throw new Error(result.message || 'Failed to connect to database');
            }
        } catch (error) {
            console.error('❌ Database connection failed:', error);
            this.updateConnectionStatus('disconnected', 'Connection failed');
            this.showNotification(`Database connection failed: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    }

    displaySchemaInfo(schemaInfo) {
        const schemaPanel = document.getElementById('schemaPanel');
        const schemaStats = document.getElementById('schemaStats');
        const tablesGrid = document.getElementById('tablesGrid');

        // Show schema panel
        schemaPanel.classList.remove('hidden');

        // Display statistics
        const stats = schemaInfo.statistics || {};
        schemaStats.innerHTML = `
            <div class="stat-card">
                <div class="stat-number">${Object.keys(schemaInfo.tables).length}</div>
                <div class="stat-label">Tables</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">${stats.total_rows || 0}</div>
                <div class="stat-label">Total Rows</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">${stats.database_size_mb || 0} MB</div>
                <div class="stat-label">Database Size</div>
            </div>
        `;

        // Display tables
        tablesGrid.innerHTML = '';
        Object.entries(schemaInfo.tables).forEach(([tableName, tableInfo]) => {
            const tableCard = document.createElement('div');
            tableCard.className = 'table-card';
            
            const columnsHtml = tableInfo.columns.slice(0, 5).map(col => `
                <div class="column-item">
                    <span>${col.name}</span>
                    <span style="color: var(--text-light); font-size: 0.7rem;">${col.type}</span>
                </div>
            `).join('');

            tableCard.innerHTML = `
                <div class="table-header">
                    <div class="table-name">${tableName}</div>
                    <div class="table-purpose">${tableInfo.purpose || 'unknown'}</div>
                </div>
                <div class="table-info">
                    ${tableInfo.columns.length} columns • ${tableInfo.row_count} rows
                </div>
                <div class="columns-list">
                    ${columnsHtml}
                    ${tableInfo.columns.length > 5 ? `<div style="padding: 0.25rem 0; color: var(--text-light);">... and ${tableInfo.columns.length - 5} more columns</div>` : ''}
                </div>
            `;
            
            tablesGrid.appendChild(tableCard);
        });
    }

    async uploadDocuments() {
        const fileInput = document.getElementById('documentsFile');
        const files = fileInput.files;
        
        if (files.length === 0) {
            this.showNotification('Please select documents to upload', 'error');
            return;
        }

        this.showLoading('🤖 Processing documents with all-MiniLM-L6-v2...');

        try {
            const formData = new FormData();
            Array.from(files).forEach(file => {
                formData.append('files', file);
            });

            const response = await fetch(`${this.apiBaseUrl}/ingestion/upload-documents`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                this.displayDocumentStatus(result);
                this.showNotification(`Processed ${result.processed_documents.length} documents with ${result.embeddings_generated} embeddings`, 'success');
                console.log('✅ Documents processed:', result);
            } else {
                throw new Error(result.message || 'Failed to process documents');
            }
        } catch (error) {
            console.error('❌ Document processing failed:', error);
            this.showNotification(`Document processing failed: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    }

    displayDocumentStatus(result) {
        const statusElement = document.getElementById('documentStatus');
        statusElement.innerHTML = `
            <div style="margin-top: 1rem; padding: 1rem; background: var(--bg-secondary); border-radius: var(--radius-md);">
                <h4>📊 Processing Results</h4>
                <p>✅ Processed: ${result.processed_documents.length} documents</p>
                <p>🧩 Total chunks: ${result.total_chunks}</p>
                <p>🤖 Embeddings generated: ${result.embeddings_generated}</p>
                <p>📐 Model: sentence-transformers/all-MiniLM-L6-v2</p>
            </div>
        `;
    }

    async executeQuery() {
        const queryInput = document.getElementById('queryInput');
        const query = queryInput.value.trim();

        if (!query) {
            this.showNotification('Please enter a query', 'error');
            return;
        }

        if (!this.databasePath) {
            this.showNotification('Please connect to a database first', 'error');
            return;
        }

        this.showLoading('🧠 Processing natural language query...');

        try {
            const response = await fetch(`${this.apiBaseUrl}/query/execute`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: query,
                    database_path: this.databasePath,
                    include_documents: true
                })
            });

            const result = await response.json();

            if (result.success) {
                this.displayQueryResults(result);
                this.showNotification(`Query executed in ${result.execution_time.toFixed(2)}s`, 'success');
                console.log('✅ Query executed:', result);
            } else {
                throw new Error(result.message || 'Failed to execute query');
            }
        } catch (error) {
            console.error('❌ Query execution failed:', error);
            this.showNotification(`Query failed: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    }

    displayQueryResults(result) {
        const resultsPanel = document.getElementById('resultsPanel');
        const queryInfo = document.getElementById('queryInfo');
        const databaseResultsContainer = document.getElementById('databaseResultsContainer');
        const documentResultsContainer = document.getElementById('documentResultsContainer');

        // Show results panel
        resultsPanel.classList.remove('hidden');

        // Display query info
        queryInfo.innerHTML = `
            <div><strong>Query:</strong> ${result.query}</div>
            <div><strong>SQL Generated:</strong> <code>${result.sql_query || 'None'}</code></div>
            <div><strong>Confidence:</strong> ${(result.confidence * 100).toFixed(1)}%</div>
            <div><strong>Execution Time:</strong> ${result.execution_time.toFixed(2)}s</div>
        `;

        // Display database results
        if (result.results && result.results.length > 0) {
            const table = this.createResultsTable(result.results);
            databaseResultsContainer.innerHTML = `
                <h4>📊 Database Results (${result.results.length} rows)</h4>
                ${table}
            `;
        } else {
            databaseResultsContainer.innerHTML = '<p>No database results found.</p>';
        }

        // Display document results
        if (result.document_results && result.document_results.length > 0) {
            const documentsHtml = result.document_results.map(doc => `
                <div class="document-result">
                    <div class="document-header">
                        <div class="document-name">${doc.file_name}</div>
                        <div class="similarity-score">${(doc.similarity * 100).toFixed(1)}%</div>
                    </div>
                    <div class="document-content">${doc.chunk_content}</div>
                </div>
            `).join('');
            
            documentResultsContainer.innerHTML = `
                <h4>📄 Document Results (${result.document_results.length} matches)</h4>
                ${documentsHtml}
            `;
        } else {
            documentResultsContainer.innerHTML = '<p>No document results found.</p>';
        }
    }

    createResultsTable(results) {
        if (!results || results.length === 0) {
            return '<p>No results to display.</p>';
        }

        const columns = Object.keys(results[0]);
        const headerRow = columns.map(col => `<th>${col}</th>`).join('');
        const dataRows = results.map(row => {
            const cells = columns.map(col => `<td>${row[col] !== null ? row[col] : '-'}</td>`).join('');
            return `<tr>${cells}</tr>`;
        }).join('');

        return `
            <table class="results-table">
                <thead>
                    <tr>${headerRow}</tr>
                </thead>
                <tbody>
                    ${dataRows}
                </tbody>
            </table>
        `;
    }

    async explainQuery() {
        const queryInput = document.getElementById('queryInput');
        const query = queryInput.value.trim();

        if (!query) {
            this.showNotification('Please enter a query', 'error');
            return;
        }

        this.showLoading('💡 Explaining query processing...');

        try {
            const response = await fetch(`${this.apiBaseUrl}/query/explain`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: query,
                    database_path: this.databasePath
                })
            });

            const result = await response.json();

            if (result.success) {
                this.displayQueryExplanation(result.explanation);
                console.log('💡 Query explained:', result);
            } else {
                throw new Error(result.message || 'Failed to explain query');
            }
        } catch (error) {
            console.error('❌ Query explanation failed:', error);
            this.showNotification(`Query explanation failed: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    }

    displayQueryExplanation(explanation) {
        const explanationHtml = `
            <div style="background: var(--bg-secondary); padding: 1.5rem; border-radius: var(--radius-lg); margin-top: 1rem;">
                <h3>💡 Query Explanation</h3>
                <div style="margin-top: 1rem;">
                    <p><strong>Query Type:</strong> ${explanation.query_type}</p>
                    <p><strong>Confidence:</strong> ${(explanation.confidence * 100).toFixed(1)}%</p>
                    <p><strong>Generated SQL:</strong></p>
                    <code style="background: var(--bg-tertiary); padding: 0.5rem; border-radius: var(--radius-sm); display: block; margin: 0.5rem 0;">${explanation.generated_sql || 'None generated'}</code>
                    <p><strong>Explanation:</strong></p>
                    <p style="font-style: italic; margin-top: 0.5rem;">${explanation.explanation_text}</p>
                </div>
            </div>
        `;

        // Insert explanation after query input
        const queryPanel = document.getElementById('queryPanel');
        const existingExplanation = queryPanel.querySelector('.query-explanation');
        if (existingExplanation) {
            existingExplanation.remove();
        }

        const explanationDiv = document.createElement('div');
        explanationDiv.className = 'query-explanation';
        explanationDiv.innerHTML = explanationHtml;
        queryPanel.querySelector('.panel-content').appendChild(explanationDiv);
    }

    async getQuerySuggestions() {
        if (!this.databasePath) {
            this.showNotification('Please connect to a database first', 'error');
            return;
        }

        this.showLoading('💭 Generating query suggestions...');

        try {
            const response = await fetch(`${this.apiBaseUrl}/query/suggestions?database_path=${encodeURIComponent(this.databasePath)}`);
            const result = await response.json();

            if (result.success) {
                this.displayQuerySuggestions(result.suggestions);
                console.log('💭 Query suggestions:', result);
            } else {
                throw new Error(result.message || 'Failed to get suggestions');
            }
        } catch (error) {
            console.error('❌ Query suggestions failed:', error);
            this.showNotification(`Failed to get suggestions: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    }

    displayQuerySuggestions(suggestions) {
        const suggestionsContainer = document.getElementById('suggestionsContainer');
        const suggestionsList = document.getElementById('suggestionsList');

        suggestionsList.innerHTML = '';
        suggestions.forEach(suggestion => {
            const suggestionItem = document.createElement('div');
            suggestionItem.className = 'suggestion-item';
            suggestionItem.textContent = suggestion.query;
            suggestionItem.title = `Category: ${suggestion.category}`;
            
            suggestionItem.addEventListener('click', () => {
                document.getElementById('queryInput').value = suggestion.query;
                document.getElementById('executeQueryButton').disabled = false;
                document.getElementById('explainQueryButton').disabled = false;
                suggestionsContainer.classList.add('hidden');
            });
            
            suggestionsList.appendChild(suggestionItem);
        });

        suggestionsContainer.classList.remove('hidden');
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.nlpQueryEngine = new NLPQueryEngine();
});