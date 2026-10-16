/**
 * 문의 답변 이메일의 백그라운드 발송 상태를 주기적으로 확인합니다.
 * 발송이 끝난 뒤에만 화면을 새로고침하여 DB의 답변 완료 상태와 발송 시간을
 * 한 번에 반영하므로, 사용자가 직접 새로고침할 필요가 없습니다.
 */
(() => {
    "use strict";

    const POLL_INTERVAL_MS = 1_000;
    const MAX_POLL_DURATION_MS = 120_000;
    const COMPLETED_STATUS = "replied";
    const IN_PROGRESS_STATUS = "in_progress";
    const initializedTrackers = new WeakSet();

    function initializeTracker(tracker) {
        if (initializedTrackers.has(tracker)) return;
        initializedTrackers.add(tracker);

        if (tracker.dataset.status !== IN_PROGRESS_STATUS) return;

        const startedAt = Date.now();
        const statusUrl = tracker.dataset.statusUrl;

        const pollStatus = async () => {
            if (!document.contains(tracker)) return;

            if (Date.now() - startedAt >= MAX_POLL_DURATION_MS) {
                tracker.textContent = "이메일 발송이 지연되고 있습니다. 잠시 후 다시 확인해 주세요.";
                return;
            }

            try {
                const response = await fetch(statusUrl, {
                    credentials: "same-origin",
                    headers: {"X-Requested-With": "XMLHttpRequest"},
                });
                if (!response.ok) throw new Error("발송 상태를 조회하지 못했습니다.");

                const result = await response.json();
                tracker.dataset.status = result.status;
                const shouldRefreshPage = tracker.dataset.refreshOnComplete === "true";
                tracker.textContent = shouldRefreshPage
                    ? result.message
                    : result.status_label;

                if (result.is_complete || result.status === COMPLETED_STATUS) {
                    if (shouldRefreshPage) {
                        // 상세 화면은 상태 외에 답변일과 메일 발송일도 있으므로 서버
                        // 값을 한 번에 반영하기 위해 완료 시 한 번만 갱신합니다.
                        window.location.reload();
                    }
                    // 목록 화면은 현재 셀의 문구가 이미 '답변 완료'로 바뀌었으므로
                    // 페이지를 갱신하지 않고 폴링만 종료합니다.
                    return;
                }
            } catch (error) {
                // 일시적인 네트워크 오류는 다음 조회에서 회복할 수 있으므로 화면을
                // 오류 페이지로 보내지 않고 상태 문구만 갱신합니다.
                tracker.textContent = "발송 완료 여부를 다시 확인하고 있습니다.";
            }

            window.setTimeout(pollStatus, POLL_INTERVAL_MS);
        };

        window.setTimeout(pollStatus, POLL_INTERVAL_MS);
    }

    function initializeVisibleTrackers(root = document) {
        root.querySelectorAll("[data-contact-delivery-status]").forEach(initializeTracker);
    }

    document.addEventListener("DOMContentLoaded", () => initializeVisibleTrackers());

    // SmartBase 관리자는 페이지 이동 시 본문만 동적으로 교체하므로 새로 표시된
    // 문의 상세 화면도 놓치지 않도록 추가된 DOM에서 추적 요소를 다시 찾습니다.
    new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            for (const node of mutation.addedNodes) {
                if (!(node instanceof Element)) continue;
                if (node.matches("[data-contact-delivery-status]")) {
                    initializeTracker(node);
                }
                initializeVisibleTrackers(node);
            }
        }
    }).observe(document.documentElement, {childList: true, subtree: true});
})();
