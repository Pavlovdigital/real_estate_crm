document.addEventListener('DOMContentLoaded', function() {
    const olxButton = document.getElementById('run-olx-parser');
    const krishaButton = document.getElementById('run-krisha-parser');
    const progressBar = document.getElementById('parser-progress-bar');
    const progressContainer = document.querySelector('.progress'); // For hiding/showing
    const parserLogOutput = document.getElementById('parser-log-output');
    const parserCurrentTask = document.getElementById('parser-current-task');
    const lastRunSummaryDiv = document.getElementById('last-run-summary-display'); // To update after completion

    let pollingIntervalId = null;
    let currentLogLength = 0; // To track new log messages

    function updateUIInProgress(isParsing) {
        if (isParsing) {
            if (olxButton) olxButton.disabled = true;
            if (krishaButton) krishaButton.disabled = true;
            if (progressContainer) progressContainer.style.display = 'block';
            if (progressBar) progressBar.style.width = '0%';
            if (progressBar) progressBar.textContent = '0%';
            if (parserLogOutput) parserLogOutput.innerHTML = ''; // Clear previous logs
            if (parserCurrentTask) parserCurrentTask.textContent = 'Инициализация...';
            currentLogLength = 0;
        } else {
            if (olxButton) olxButton.disabled = false;
            if (krishaButton) krishaButton.disabled = false;
            // Optionally hide progress bar on completion or keep it at 100%
            // if (progressContainer) progressContainer.style.display = 'none'; 
        }
    }

    function fetchStatus() {
        fetch("{{ url_for('admin.parser_status_route') }}") // This will be templated by Flask if JS is in template
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Ошибка сети: ${response.status} ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                if (progressBar) {
                    progressBar.style.width = data.progress_percent + '%';
                    progressBar.textContent = data.progress_percent + '%';
                }
                if (parserCurrentTask) parserCurrentTask.textContent = data.current_task || 'Нет текущей задачи.';
                
                if (parserLogOutput && data.log) {
                    // Append only new log messages
                    const newLogEntries = data.log.slice(currentLogLength);
                    newLogEntries.forEach(logEntry => {
                        const p = document.createElement('p');
                        p.textContent = logEntry;
                        parserLogOutput.appendChild(p);
                    });
                    currentLogLength = data.log.length;
                    parserLogOutput.scrollTop = parserLogOutput.scrollHeight; // Auto-scroll
                }

                if (data.complete) {
                    clearInterval(pollingIntervalId);
                    pollingIntervalId = null;
                    updateUIInProgress(false);
                    if (parserCurrentTask) parserCurrentTask.textContent = data.current_task || "Задача завершена.";
                    if (data.error) {
                        if (parserLogOutput) {
                             const p = document.createElement('p');
                             p.className = 'text-danger fw-bold';
                             p.textContent = `ОШИБКА: ${data.error}`;
                             parserLogOutput.appendChild(p);
                        }
                        alert(`Произошла ошибка: ${data.error}`);
                    } else if (data.summary) {
                         if (parserLogOutput) {
                             const p = document.createElement('p');
                             p.className = 'text-success fw-bold';
                             p.textContent = `ЗАВЕРШЕНО: Добавлено: ${data.summary.added}, Обновлено: ${data.summary.updated}, Ошибки: ${data.summary.errors}, Пропущено: ${data.summary.skipped}`;
                             parserLogOutput.appendChild(p);
                         }
                        // Update last run summary display on the page
                        if(lastRunSummaryDiv) {
                            lastRunSummaryDiv.innerHTML = `
                                <p><strong>Сводка последнего запуска:</strong></p>
                                <ul>
                                    <li>Добавлено: ${data.summary.added}</li>
                                    <li>Обновлено: ${data.summary.updated}</li>
                                    <li>Ошибок: ${data.summary.errors}</li>
                                    <li>Пропущено: ${data.summary.skipped}</li>
                                </ul>`;
                        }
                    }
                }
            })
            .catch(error => {
                console.error("Ошибка при получении статуса парсера:", error);
                if (parserCurrentTask) parserCurrentTask.textContent = `Ошибка обновления статуса: ${error.message}`;
                // Consider stopping polling on certain types of errors
                // clearInterval(pollingIntervalId);
                // updateUIInProgress(false);
            });
    }

    function startPolling() {
        if (pollingIntervalId) {
            clearInterval(pollingIntervalId);
        }
        fetchStatus(); // Initial fetch
        pollingIntervalId = setInterval(fetchStatus, 3000); // Poll every 3 seconds
    }

    function triggerParser(sourceUrl) {
        updateUIInProgress(true);
        if (parserCurrentTask) parserCurrentTask.textContent = 'Отправка запроса на запуск парсера...';

        fetch(sourceUrl, { method: 'POST' }) // Assuming POST as per best practice for actions
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => {throw new Error(`Ошибка запуска: ${err.message || response.statusText}`)});
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'started') {
                    if (parserCurrentTask) parserCurrentTask.textContent = data.message || 'Парсер запущен, ожидание первого обновления статуса...';
                    startPolling();
                } else {
                    throw new Error(data.message || 'Не удалось запустить парсер.');
                }
            })
            .catch(error => {
                console.error(`Ошибка при запуске парсера (${sourceUrl}):`, error);
                alert(`Не удалось запустить парсер: ${error.message}`);
                if (parserCurrentTask) parserCurrentTask.textContent = `Ошибка запуска: ${error.message}`;
                updateUIInProgress(false);
            });
    }

    if (olxButton) {
        olxButton.addEventListener('click', function() {
            // The URL for admin.run_olx_parser_route needs to be available to JS
            // This is often done by embedding it in a data attribute or using Flask's url_for in a script tag within the HTML
            triggerParser(this.dataset.runUrl || "{{ url_for('admin.run_olx_parser_route') }}"); 
        });
    }

    if (krishaButton) {
        krishaButton.addEventListener('click', function() {
            triggerParser(this.dataset.runUrl || "{{ url_for('admin.run_krisha_parser_route') }}");
        });
    }
    
    // Check initial status on page load in case a task was already running (less likely with simple threading)
    // fetchStatus(); // Or, if session might persist status across page loads.
    // For this setup, better to start clean unless a more robust task queue is used.
    if (progressContainer) progressContainer.style.display = 'none'; // Initially hide progress
});
