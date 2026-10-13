/**
 * NutriScan - Módulo de Compartilhamento e Exportação de Dieta
 * Suporte a Web Share API nativo (Android), fallback WhatsApp Web,
 * cópia para Área de Transferência com Toast, e Impressão / PDF limpo.
 */
(function (window) {
    'use strict';

    function showToast(message, duration = 3000) {
        let toast = document.getElementById('nutriscan-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'nutriscan-toast';
            toast.className = 'ns-toast';
            toast.setAttribute('role', 'status');
            toast.setAttribute('aria-live', 'polite');
            document.body.appendChild(toast);
        }

        toast.textContent = message;
        toast.classList.add('show');

        if (toast._timeout) {
            clearTimeout(toast._timeout);
        }

        toast._timeout = setTimeout(() => {
            toast.classList.remove('show');
        }, duration);
    }

    async function shareToWhatsApp(summaryText) {
        if (!summaryText) {
            showToast('Nenhum texto de resumo para compartilhar.');
            return;
        }

        // Tenta Web Share API nativo se suportado (folha nativa do Android)
        if (navigator.share) {
            try {
                await navigator.share({
                    title: 'NutriScan Dieta',
                    text: summaryText,
                });
                return;
            } catch (err) {
                // Se o usuário cancelou a folha nativa, não dispara fallback
                if (err && err.name === 'AbortError') {
                    return;
                }
            }
        }

        // Fallback: abre no WhatsApp Web / App
        const url = `https://api.whatsapp.com/send?text=${encodeURIComponent(summaryText)}`;
        window.open(url, '_blank', 'noopener,noreferrer');
    }

    async function copyToClipboard(summaryText) {
        if (!summaryText) {
            showToast('Nenhum texto de resumo para copiar.');
            return;
        }

        try {
            if (navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(summaryText);
            } else {
                // Fallback para navegadores legados
                const ta = document.createElement('textarea');
                ta.value = summaryText;
                ta.style.position = 'fixed';
                ta.style.left = '-9999px';
                document.body.appendChild(ta);
                ta.focus();
                ta.select();
                document.execCommand('copy');
                document.body.removeChild(ta);
            }
            showToast('Resumo copiado para a área de transferência!');
        } catch (err) {
            console.error('Erro ao copiar para clipboard:', err);
            showToast('Erro ao copiar texto.');
        }
    }

    function printDailyReport() {
        window.print();
    }

    async function fetchExport(dateStr, format = 'whatsapp') {
        const params = new URLSearchParams();
        if (dateStr) params.set('date_str', dateStr);
        if (format) params.set('format', format);

        const res = await fetch(`/api/v1/diet/export?${params.toString()}`);
        if (!res.ok) {
            throw new Error(`Falha ao exportar dieta: ${res.status}`);
        }
        return await res.json();
    }

    window.NutriScanShare = {
        shareToWhatsApp,
        copyToClipboard,
        printDailyReport,
        fetchExport,
        showToast,
    };
})(window);
