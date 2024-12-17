document.addEventListener('DOMContentLoaded', () => {
    let selectedCell = null;

    document.querySelectorAll('.cell').forEach(cell => {
        cell.addEventListener('click', () => {
            if (selectedCell) {
                const from = selectedCell.dataset.position;
                const to = cell.dataset.position;

                // Отправляем ход на сервер
                fetch('/move', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ from, to })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        // Обновляем доску
                        cell.innerHTML = selectedCell.innerHTML;
                        selectedCell.innerHTML = '';
                    } else {
                        alert(data.message);
                    }
                });

                selectedCell = null;
            } else {
                selectedCell = cell;
            }
        });
    });
}); 