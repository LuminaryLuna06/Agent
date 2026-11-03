# Kiến Trúc Hệ Thống Shorekeeper Agent

> **Tài liệu sống (Living Document):** Tài liệu này phản ánh trung thực trạng thái kiến trúc hiện tại của dự án Shorekeeper Agent. Mọi thay đổi kiến trúc, luồng xử lý hoặc cấu trúc dữ liệu **bắt buộc phải được cập nhật đồng thời trong cùng Pull Request (PR)**.

| Thông Tin | Chi Tiết |
| :--- | :--- |
| **Dự án** | Shorekeeper Agent |
| **Phiên bản tài liệu** | 1.0.0 |
| **Ngày cập nhật gần nhất** | 2026-10-30 |
| **Trạng thái** | Active / Maintained |
| **Chính sách PR** | **Docs-as-Code** — Bắt buộc review & update khi sửa đổi core / db / llm / tokens |

---

## 1. Tổng Quan Hệ Thống (System Overview)

**Shorekeeper Agent** là một hệ thống AI Agent độc lập, hướng tới khả năng trò chuyện bền bỉ, nhận thức ngữ cảnh thời gian thực và quản lý tài nguyên token nghiêm ngặt. Hệ thống được thiết kế theo các nguyên tắc cốt lõi:

*   **Ngân sách Token Tất định (Strict Token Budgeting):** Sử dụng chiến lược dynamic budgeting và xếp lịch *newest-first* để cửa sổ ngữ cảnh không bao giờ vượt ngưỡng giới hạn của LLM backend.
*   **Ký Ức Bền Vững (Persistent Storage):** Lưu trữ toàn bộ lịch sử tin nhắn, trạng thái runtime và nhật ký suy luận (Tick Log) vào SQLite thông qua SQLAlchemy ORM.
*   **Quan Sát Toàn Diện (Full Observability):** Ghi nhận đầy đủ Prompt nguyên bản, chuỗi suy nghĩ (Thinking / Reasoning trace) và phản hồi của LLM sau mỗi lượt hội thoại.
*   **Kiến Trúc Mô-đun (Decoupled Modularity):** Phân tách rành mạch giữa lớp lưu trữ dữ liệu, tính toán token, tạo prompt và giao tiếp LLM.

---

## 2. Sơ Đồ Kiến Trúc Tổng Thể (High-Level Architecture)

Biểu đồ dưới đây mô tả luồng giao tiếp giữa người dùng, tầng điều phối (Orchestrator), các hệ thống con và cơ sở dữ liệu:

```mermaid
flowchart TB
    subgraph ClientLayer["Lớp Tương Tác (Client Layer)"]
        User(["User / Luna"])
        Runner["Runner (main.py / Notebook)"]
    end

    subgraph AgentCore["Hệ Thống Lõi (src/agent)"]
        Agent["ShorekeeperAgent<br/>(Turn Orchestrator)"]
    end

    subgraph Subsystems["Các Phân Hệ Hỗ Trợ (Subsystems)"]
        direction TB
        TokenBudget["Token Manager (src/tokens)<br/>• Dynamic Budgeting<br/>• TikToken Counter<br/>• Fit Newest-First"]
        PromptBuilder["Prompt Builder (src/prompts)<br/>• Persona & Voice Anchors<br/>• System Prompt Layout"]
        LLMClient["LLM Client (src/llm)<br/>• OpenAI Compatible API<br/>• Thinking/Reasoning Stream"]
    end

    subgraph StorageLayer["Tầng Lưu Trữ (src/db)"]
        Repo["Repository Layer"]
        DB[(SQLite Database<br/>test.db)]
    end

    subgraph ExternalServices["Dịch Vụ Ngoại Vi"]
        LLMBackend["LLM Inference Server<br/>(Llama.cpp / vLLM / Gemma4-12B)"]
    end

    %% Flow connections
    User -->|Nhập tin nhắn| Runner
    Runner -->|agent.step| Agent

    Agent <-->|Phân bổ ngân sách & cắt tỉa| TokenBudget
    Agent <-->|Ghép Persona, Lịch sử, Anchor| PromptBuilder
    Agent -->|Gọi suy luận| LLMClient
    LLMClient <-->|HTTP POST /v1/chat/completions| LLMBackend

    Agent -->|Lưu tin nhắn, TickLog & State| Repo
    Repo <-->|SQLAlchemy Engine / Session| DB
    Agent -->|Phản hồi câu trả lời| Runner
    Runner -->|Hiển thị phản hồi| User
```

---

## 3. Cấu Trúc Các Thành Phần (Component Architecture)

```
src/
├── agent/       # Bộ điều phối vòng đời (Lifecycle & Turn Orchestrator)
├── config/      # Cấu hình môi trường & hằng số hệ thống (Pydantic Settings)
├── db/          # Tầng lưu trữ: ORM Models, Repository CRUD, SessionLocal
├── llm/         # HTTP Client gọi Backend suy luận & Schema tham số
├── prompts/     # Xây dựng System Prompt, Persona Core và Voice Anchors
└── tokens/      # Định lượng token và giải thuật tối ưu hóa Context Window
```

### 3.1. Agent Orchestrator (`src/agent/agent.py`)
Đóng vai trò là trung tâm chỉ huy:
1.  Khởi tạo ngân sách token (`dynamic_budget`).
2.  Xây dựng System Prompt ban đầu theo định mức token cho phép.
3.  Tải lịch sử hội thoại gần nhất và cắt tỉa theo thuật toán `fit_newest_first`.
4.  Thực hiện phương thức `step(user_msg)` để vận hành chu kỳ một lượt nói chuyện.

### 3.2. Token & Budget Management (`src/tokens/`)
*   **`budget.py`**: Chia nhỏ tổng `CONTEXT_WINDOW` (mặc định 4096 hoặc 8192) thành các ngăn:
    *   `persona`: Định nghĩa nhân cách lõi.
    *   `anchor`: Mỏ neo giọng điệu (đặt ở cuối prompt để giữ vững tính cách).
    *   `chat`: Dành cho lịch sử hội thoại gần nhất (cắt tỉa theo cơ chế newest-first).
    *   `reply`: Ngân sách bảo lưu cho câu trả lời của mô hình.
*   **`counter.py`**: Sử dụng thư viện `tiktoken` (bộ mã hóa `cl100k_base`) để đếm token chuẩn xác, kèm thuật toán heuristic dự phòng khi offline.

### 3.3. Prompt Engineering (`src/prompts/`)
*   **`templates.py`**: Định hình bản sắc của Shorekeeper (người bảo vệ Black Shores, phong thái điềm tĩnh, dịu dàng, thông tuệ).
*   **`builder.py`**: Lắp ráp prompt theo trật tự logic:
    $$\text{Prompt} = [\text{System Persona}] + [\text{Recent Chat History}] + [\text{Voice Anchor}]$$

### 3.4. LLM Client (`src/llm/`)
*   Giao tiếp với các endpoint tương thích OpenAI (`/v1/chat/completions`).
*   Hỗ trợ cấu hình mô hình, nhiệt độ (temperature), chuỗi suy nghĩ (`enable_thinking`, `reasoning_effort`).
*   Bóc tách riêng chuỗi suy nghĩ (`reasoning`) và nội dung trả lời (`output`).

### 3.5. Persistence Layer (`src/db/`)
*   Quản lý phiên làm việc SQLite thông qua SQLAlchemy 2.0.
*   Thực thi lưu vết tự động: tin nhắn người dùng, tin nhắn phản hồi, trạng thái thời gian thực (`StateField`) và nhật ký mỗi tick (`TickLog`).

---

## 4. Chu Trình Thực Thi Một Lượt Hội Thoại (Turn Execution Lifecycle)

Biểu đồ tuần tự dưới đây mô tả chính xác những gì diễn ra trong hàm `agent.step(user_msg)`:

```mermaid
sequenceDiagram
    autonumber
    actor User as Người dùng
    participant Runner as Runner (main.py)
    participant Agent as ShorekeeperAgent
    participant Repo as DB Repository
    participant Budget as Token Budgeter
    participant LLM as LLM Client
    participant DB as SQLite DB

    User->>Runner: Gửi câu lệnh / tin nhắn mới
    Runner->>Agent: step(user_msg)
    
    %% Bước 1: Lưu tin nhắn người dùng
    Agent->>Repo: save_message(role="user", content=user_msg)
    Repo->>DB: INSERT INTO messages
    DB-->>Repo: user_record

    %% Bước 2: Cân đối Token & Build Prompt
    Agent->>Budget: fit_newest_first(history + user_msg, chat_budget)
    Budget-->>Agent: truncated_messages
    Note over Agent: Ghép system_prompt + truncated_messages

    %% Bước 3: Suy luận LLM
    Agent->>LLM: llm_call(all_prompt_messages, config)
    LLM-->>Agent: response, reasoning_text

    %% Bước 4: Lưu trữ phản hồi và Tick Log
    alt Suy luận thành công
        Agent->>Repo: save_message(role="assistant", content=response)
        Repo->>DB: INSERT INTO messages
        
        Agent->>Repo: log_tick(trigger="user_message", prompt, output, thinking, params)
        Repo->>DB: INSERT INTO tick_log
        
        Agent->>Repo: update_state("last_message_ts", timestamp)
        Repo->>DB: UPSERT state
        
        Agent-->>Runner: response
        Runner-->>User: Hiển thị câu trả lời
    else Lỗi suy luận / Phản hồi rỗng
        Agent-->>Runner: None
        Runner-->>User: Thông báo lỗi / Thử lại
    end
```

---

## 5. Sơ Đồ Cơ Sở Dữ Liệu (Entity Relationship Diagram)

Hệ thống sử dụng mô hình cơ sở dữ liệu nhẹ, tối ưu cho tốc độ đọc/ghi cục bộ:

```mermaid
erDiagram
    MESSAGES {
        int id PK "Khóa chính tự tăng"
        float ts "Thời gian UNIX Epoch (Index)"
        string role "Vai trò: user | assistant"
        text content "Nội dung tin nhắn"
    }

    STATE {
        string key PK "Tên biến trạng thái (vd: last_message_ts)"
        text value "Giá trị lưu trữ"
        float updated_at "Thời điểm cập nhật"
    }

    TICK_LOG {
        int id PK "Khóa chính tự tăng"
        float ts "Thời điểm thực thi tick (Index)"
        string trigger "Nguyên nhân kích hoạt (vd: user_message)"
        int last_msg_id "ID tin nhắn kích hoạt gần nhất"
        text prompt "Toàn bộ chuỗi prompt đưa vào LLM"
        text thinking "Chuỗi suy nghĩ tách biệt của LLM"
        text output "Phản hồi thô trả về"
        json params "Tham số LLMConfig lúc chạy"
    }

    MESSAGES ||--o{ TICK_LOG : "last_msg_id tham chiếu"
```

---

## 6. Quy Định Đồng Bộ Kiến Trúc Với Pull Request (PR Governance)

Để kiến trúc hệ thống không bị lỗi thời theo thời gian, mọi kỹ sư và cộng tác viên **phải tuân thủ quy tắc đồng bộ bắt buộc**:

> [!IMPORTANT]
> ### Nguyên Tắc "Docs as Code"
> Bất kỳ Pull Request (PR) nào làm thay đổi một trong các khía cạnh dưới đây **bắt buộc phải cập nhật file `docs/architecture.md` trong cùng PR đó**:
> 1. **Thay đổi mô hình dữ liệu (`src/db/models.py`)**: Bổ sung bảng mới, trường mới hoặc thay đổi quan hệ trong ERD.
> 2. **Thay đổi luồng hội thoại (`src/agent/agent.py`)**: Sửa đổi quy trình các bước trong hàm `step()` hoặc thêm lifecycle hooks.
> 3. **Thay đổi cấu trúc phân bổ Token (`src/tokens/`)**: Đổi thuật toán ngân sách hoặc chia lại tỷ trọng persona/chat/reply.
> 4. **Thay đổi giao thức LLM (`src/llm/`)**: Thêm provider mới, cấu trúc lại streaming hoặc cơ chế reasoning.

### Checklist Kiểm Duyệt Pull Request (PR Reviewer Checklist)
Khi review một PR, reviewer cần tích chọn:
* [ ] Mã nguồn đã được kiểm thử với `pytest` đạt 100% pass.
* [ ] Kiến trúc có thay đổi không? Nếu có:
  * [ ] Đã cập nhật mục tương ứng trong `docs/architecture.md`.
  * [ ] Đã cập nhật Mermaid diagram tương ứng nếu luồng thay đổi.
  * [ ] Đã cập nhật trường **Ngày cập nhật gần nhất** ở đầu file này thành ngày hiện tại (`YYYY-MM-DD`).
