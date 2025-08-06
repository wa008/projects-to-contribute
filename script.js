
document.addEventListener('DOMContentLoaded', () => {
    const projectsTable = document.querySelector('#projects-table tbody');
    const tableHeaders = document.querySelectorAll('#projects-table th');
    const lastUpdatedSpan = document.querySelector('#last-updated');
    const languageFilter = document.querySelector('#language-filter');
    const keywordFilter = document.querySelector('#keyword-filter');
    const loader = document.querySelector('#loader');
    const backToTopButton = document.querySelector('#back-to-top');

    let projects = [];
    let currentSort = { key: 'demand_index', order: 'desc' };

    async function fetchData() {
        loader.style.display = 'block';
        try {
            const response = await fetch('projects.json');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            projects = data.projects;
            lastUpdatedSpan.textContent = new Date(data.last_updated).toLocaleString();
            sortAndRender();
        } catch (error) {
            console.error('Error fetching project data:', error);
            projectsTable.innerHTML = `<tr><td colspan="6">Error loading data: ${error.message}</td></tr>`;
        } finally {
            loader.style.display = 'none';
        }
    }

    function renderTable(sortedProjects) {
        projectsTable.innerHTML = '';
        if (sortedProjects.length === 0) {
            projectsTable.innerHTML = '<tr><td colspan="6">No projects found.</td></tr>';
            return;
        }

        sortedProjects.slice(0, 100).forEach((project, index) => {
            const row = document.createElement('tr');
            const keywords = project.keywords.length > 0 ? project.keywords.join(', ') : 'N/A';
            row.innerHTML = `
                <td>${index + 1}</td>
                <td><a href="${project.url}" target="_blank" rel="noopener noreferrer">${project.name}</a></td>
                <td>${project.stars.toLocaleString()}</td>
                <td>${project.new_stars_30d.toLocaleString()}</td>
                <td>${project.new_open_issues.toLocaleString()}</td>
                <td>${project.contributors.toLocaleString()}</td>
                <td>${project.demand_index.toFixed(4)}</td>
                <td>${project.language}</td>
                <td>${keywords}</td>
                <td>${new Date(project.date_fetched).toLocaleDateString()}</td>
            `;
            projectsTable.appendChild(row);
        });
    }

    function sortAndRender() {
        const filtered = filterProjects();
        const sorted = sortProjects(filtered, currentSort.key, currentSort.order);
        renderTable(sorted);
        updateSortHeaders();
    }

    function filterProjects() {
        const lang = languageFilter.value.toLowerCase().trim();
        const keyword = keywordFilter.value.toLowerCase().trim();

        return projects.filter(p => {
            const langMatch = lang ? (p.language && p.language.toLowerCase().includes(lang)) : true;
            const keywordMatch = keyword ? p.keywords.some(k => k.toLowerCase().includes(keyword)) : true;
            const starsMatch = p.stars >= 100;
            return langMatch && keywordMatch && starsMatch;
        });
    }

    function sortProjects(projects, key, order) {
        return projects.sort((a, b) => {
            let valA = a[key];
            let valB = b[key];

            if (typeof valA === 'string') {
                valA = valA.toLowerCase();
                valB = valB.toLowerCase();
            }

            if (valA < valB) return order === 'asc' ? -1 : 1;
            if (valA > valB) return order === 'asc' ? 1 : -1;
            return 0;
        });
    }

    function updateSortHeaders() {
        tableHeaders.forEach(header => {
            const key = header.dataset.sort;
            if (key) {
                header.classList.remove('sort-asc', 'sort-desc');
                if (key === currentSort.key) {
                    header.classList.add(currentSort.order === 'asc' ? 'sort-asc' : 'sort-desc');
                }
            }
        });
    }

    tableHeaders.forEach(header => {
        const key = header.dataset.sort;
        if (key) {
            header.addEventListener('click', () => {
                if (currentSort.key === key) {
                    currentSort.order = currentSort.order === 'asc' ? 'desc' : 'asc';
                } else {
                    currentSort.key = key;
                    currentSort.order = 'desc'; // Default to descending for new columns
                }
                sortAndRender();
            });
        }
    });

    // Back to top button functionality
    window.onscroll = function() {
        if (document.body.scrollTop > 20 || document.documentElement.scrollTop > 20) {
            backToTopButton.style.display = 'block';
        } else {
            backToTopButton.style.display = 'none';
        }
    };

    backToTopButton.addEventListener('click', () => {
        document.body.scrollTop = 0; // For Safari
        document.documentElement.scrollTop = 0; // For Chrome, Firefox, IE and Opera
    });

    languageFilter.addEventListener('input', sortAndRender);
    keywordFilter.addEventListener('input', sortAndRender);

    fetchData();
});
