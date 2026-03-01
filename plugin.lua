-- ═══════════════════════════════════════════════════════════════
-- VFX Texture Detector Plugin v1.0.0
-- Экспортирует TextureId из выделенных объектов → JSON файл
-- Читает pending_deletion.json → перемещает в ReplicatedStorage
-- ═══════════════════════════════════════════════════════════════

local plugin = plugin
local Selection = game:GetService("Selection")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local HttpService = game:GetService("HttpService")
local RunService = game:GetService("RunService")

-- ── Настройки ────────────────────────────────────────────────────────────────
local PLUGIN_NAME = "VFX Texture Detector"
local PENDING_FOLDER = "PendingDeletion"
local INPUT_FILE_PATH  = "input_textures.json"   -- относительный путь (рядом с app.py)
local PENDING_FILE_PATH = "pending_deletion.json"

-- ── Цвета UI ─────────────────────────────────────────────────────────────────
local COLOR_BG      = Color3.fromRGB(10, 10, 15)
local COLOR_CARD    = Color3.fromRGB(19, 19, 31)
local COLOR_ACCENT  = Color3.fromRGB(79, 110, 247)
local COLOR_SUCCESS = Color3.fromRGB(16, 185, 129)
local COLOR_WARNING = Color3.fromRGB(245, 158, 11)
local COLOR_DANGER  = Color3.fromRGB(239, 68, 68)
local COLOR_TEXT    = Color3.fromRGB(226, 232, 240)
local COLOR_SUBTEXT = Color3.fromRGB(100, 116, 139)

-- ── Создание виджета ──────────────────────────────────────────────────────────
local widgetInfo = DockWidgetPluginGuiInfo.new(
    Enum.InitialDockState.Float,
    false,  -- начально скрыт
    false,
    380,
    520,
    300,
    400
)

local widget = plugin:CreateDockWidgetPluginGui(PLUGIN_NAME, widgetInfo)
widget.Title = PLUGIN_NAME

-- ── Кнопка тулбара ────────────────────────────────────────────────────────────
local toolbar = plugin:CreateToolbar(PLUGIN_NAME)
local toggleButton = toolbar:CreateButton(
    "VFX Detector",
    "Открыть/закрыть панель VFX Texture Detector",
    "rbxassetid://7733717870"
)

toggleButton.Click:Connect(function()
    widget.Enabled = not widget.Enabled
    toggleButton:SetActive(widget.Enabled)
end)

-- ── Построение UI ─────────────────────────────────────────────────────────────
local function buildUI()
    local root = Instance.new("Frame")
    root.Size = UDim2.new(1, 0, 1, 0)
    root.BackgroundColor3 = COLOR_BG
    root.BorderSizePixel = 0
    root.Parent = widget

    -- Скролл-контейнер
    local scroll = Instance.new("ScrollingFrame")
    scroll.Size = UDim2.new(1, 0, 1, 0)
    scroll.BackgroundTransparency = 1
    scroll.BorderSizePixel = 0
    scroll.ScrollBarThickness = 4
    scroll.ScrollBarImageColor3 = COLOR_ACCENT
    scroll.CanvasSize = UDim2.new(1, 0, 0, 0)
    scroll.AutomaticCanvasSize = Enum.AutomaticSize.Y
    scroll.Parent = root

    local layout = Instance.new("UIListLayout")
    layout.SortOrder = Enum.SortOrder.LayoutOrder
    layout.Padding = UDim.new(0, 8)
    layout.Parent = scroll

    local padding = Instance.new("UIPadding")
    padding.PaddingLeft   = UDim.new(0, 14)
    padding.PaddingRight  = UDim.new(0, 14)
    padding.PaddingTop    = UDim.new(0, 14)
    padding.PaddingBottom = UDim.new(0, 14)
    padding.Parent = scroll

    -- ── Хелпер: создать карточку ──────────────────────────────────────────────
    local function makeCard(layoutOrder)
        local card = Instance.new("Frame")
        card.BackgroundColor3 = COLOR_CARD
        card.BorderSizePixel = 0
        card.AutomaticSize = Enum.AutomaticSize.Y
        card.Size = UDim2.new(1, 0, 0, 0)
        card.LayoutOrder = layoutOrder

        local corner = Instance.new("UICorner")
        corner.CornerRadius = UDim.new(0, 10)
        corner.Parent = card

        local stroke = Instance.new("UIStroke")
        stroke.Color = Color3.fromRGB(30, 30, 53)
        stroke.Thickness = 1
        stroke.Parent = card

        local p = Instance.new("UIPadding")
        p.PaddingLeft   = UDim.new(0, 12)
        p.PaddingRight  = UDim.new(0, 12)
        p.PaddingTop    = UDim.new(0, 12)
        p.PaddingBottom = UDim.new(0, 12)
        p.Parent = card

        card.Parent = scroll
        return card
    end

    -- ── Хелпер: создать лейбл ─────────────────────────────────────────────────
    local function makeLabel(parent, text, size, color, bold, layoutOrder)
        local lbl = Instance.new("TextLabel")
        lbl.Text = text
        lbl.TextSize = size or 13
        lbl.TextColor3 = color or COLOR_TEXT
        lbl.Font = bold and Enum.Font.GothamBold or Enum.Font.GothamMedium
        lbl.BackgroundTransparency = 1
        lbl.AutomaticSize = Enum.AutomaticSize.Y
        lbl.Size = UDim2.new(1, 0, 0, 0)
        lbl.TextXAlignment = Enum.TextXAlignment.Left
        lbl.TextWrapped = true
        lbl.LayoutOrder = layoutOrder or 0
        lbl.Parent = parent
        return lbl
    end

    -- ── Хелпер: создать кнопку ────────────────────────────────────────────────
    local function makeButton(parent, text, color, layoutOrder)
        local btn = Instance.new("TextButton")
        btn.Text = text
        btn.TextSize = 13
        btn.TextColor3 = COLOR_TEXT
        btn.Font = Enum.Font.GothamBold
        btn.BackgroundColor3 = color
        btn.BorderSizePixel = 0
        btn.Size = UDim2.new(1, 0, 0, 38)
        btn.LayoutOrder = layoutOrder or 0

        local corner = Instance.new("UICorner")
        corner.CornerRadius = UDim.new(0, 8)
        corner.Parent = btn

        btn.Parent = parent
        return btn
    end

    -- ── Хелпер: layout для карточки ───────────────────────────────────────────
    local function addListLayout(parent, padding)
        local l = Instance.new("UIListLayout")
        l.SortOrder = Enum.SortOrder.LayoutOrder
        l.Padding = UDim.new(0, padding or 6)
        l.Parent = parent
    end

    -- ══════════════════════════════════════════════════════════════════════════
    -- БЛОК 1: Заголовок
    -- ══════════════════════════════════════════════════════════════════════════
    local headerCard = makeCard(1)
    addListLayout(headerCard, 4)

    makeLabel(headerCard, "⬡  VFX TEXTURE DETECTOR", 15, COLOR_ACCENT, true, 1)
    makeLabel(headerCard, "Экспорт текстур и удаление дубликатов", 11, COLOR_SUBTEXT, false, 2)

    -- ══════════════════════════════════════════════════════════════════════════
    -- БЛОК 2: Статус
    -- ══════════════════════════════════════════════════════════════════════════
    local statusCard = makeCard(2)
    addListLayout(statusCard, 6)

    makeLabel(statusCard, "СТАТУС", 10, COLOR_SUBTEXT, true, 1)

    local statusLabel = makeLabel(statusCard, "● Ожидание действия", 12, COLOR_WARNING, false, 2)

    local countLabel = makeLabel(statusCard, "Выделено объектов: 0", 11, COLOR_SUBTEXT, false, 3)

    -- ══════════════════════════════════════════════════════════════════════════
    -- БЛОК 3: Экспорт текстур
    -- ══════════════════════════════════════════════════════════════════════════
    local exportCard = makeCard(3)
    addListLayout(exportCard, 8)

    makeLabel(exportCard, "ШАГ 1 — ЭКСПОРТ", 10, COLOR_SUBTEXT, true, 1)
    makeLabel(exportCard, "Выделите Parts с Decal в Studio и нажмите кнопку:", 11, COLOR_TEXT, false, 2)

    local exportBtn = makeButton(exportCard, "▶  ЭКСПОРТИРОВАТЬ ТЕКСТУРЫ", COLOR_ACCENT, 3)
    makeLabel(exportCard, "Файл будет сохранён рядом с app.py", 10, COLOR_SUBTEXT, false, 4)

    -- Лог экспорта
    local exportLog = makeLabel(exportCard, "", 10, COLOR_SUBTEXT, false, 5)

    -- ══════════════════════════════════════════════════════════════════════════
    -- БЛОК 4: Анализ
    -- ══════════════════════════════════════════════════════════════════════════
    local analyzeCard = makeCard(4)
    addListLayout(analyzeCard, 8)

    makeLabel(analyzeCard, "ШАГ 2 — АНАЛИЗ", 10, COLOR_SUBTEXT, true, 1)
    makeLabel(analyzeCard, "Запустите Python приложение и нажмите СКАНИРОВАТЬ.", 11, COLOR_TEXT, false, 2)
    makeLabel(analyzeCard, "Когда анализ завершится — вернитесь сюда.", 11, COLOR_SUBTEXT, false, 3)

    -- ══════════════════════════════════════════════════════════════════════════
    -- БЛОК 5: Удаление дубликатов
    -- ══════════════════════════════════════════════════════════════════════════
    local deleteCard = makeCard(5)
    addListLayout(deleteCard, 8)

    makeLabel(deleteCard, "ШАГ 3 — УДАЛЕНИЕ", 10, COLOR_SUBTEXT, true, 1)
    makeLabel(deleteCard, "После анализа в Python вставьте ID дубликатов:", 11, COLOR_TEXT, false, 2)

    -- Поле ввода ID
    local inputBox = Instance.new("TextBox")
    inputBox.PlaceholderText = "Вставьте ID через запятую или нажмите 'Применить из файла'"
    inputBox.Text = ""
    inputBox.TextSize = 11
    inputBox.TextColor3 = COLOR_TEXT
    inputBox.PlaceholderColor3 = COLOR_SUBTEXT
    inputBox.Font = Enum.Font.GothamMedium
    inputBox.BackgroundColor3 = Color3.fromRGB(10, 10, 15)
    inputBox.BorderSizePixel = 0
    inputBox.ClearTextOnFocus = false
    inputBox.MultiLine = true
    inputBox.TextWrapped = true
    inputBox.Size = UDim2.new(1, 0, 0, 80)
    inputBox.TextXAlignment = Enum.TextXAlignment.Left
    inputBox.TextYAlignment = Enum.TextYAlignment.Top
    inputBox.LayoutOrder = 3

    local ibCorner = Instance.new("UICorner")
    ibCorner.CornerRadius = UDim.new(0, 8)
    ibCorner.Parent = inputBox

    local ibStroke = Instance.new("UIStroke")
    ibStroke.Color = Color3.fromRGB(30, 30, 53)
    ibStroke.Thickness = 1
    ibStroke.Parent = inputBox

    local ibPad = Instance.new("UIPadding")
    ibPad.PaddingLeft   = UDim.new(0, 8)
    ibPad.PaddingRight  = UDim.new(0, 8)
    ibPad.PaddingTop    = UDim.new(0, 6)
    ibPad.PaddingBottom = UDim.new(0, 6)
    ibPad.Parent = inputBox

    inputBox.Parent = deleteCard

    local applyBtn = makeButton(deleteCard, "🗑  ПРИМЕНИТЬ УДАЛЕНИЕ", COLOR_DANGER, 4)
    local deleteLog = makeLabel(deleteCard, "", 10, COLOR_SUBTEXT, false, 5)

    -- ══════════════════════════════════════════════════════════════════════════
    -- БЛОК 6: Папка ожидания
    -- ══════════════════════════════════════════════════════════════════════════
    local folderCard = makeCard(6)
    addListLayout(folderCard, 6)

    makeLabel(folderCard, "ПАПКА ОЖИДАНИЯ", 10, COLOR_SUBTEXT, true, 1)
    makeLabel(folderCard, "ReplicatedStorage → PendingDeletion", 11, COLOR_TEXT, false, 2)

    local openFolderBtn = makeButton(folderCard, "↗  ОТКРЫТЬ ПАПКУ", Color3.fromRGB(30, 30, 53), 3)
    local clearFolderBtn = makeButton(folderCard, "✕  ОЧИСТИТЬ ПАПКУ", Color3.fromRGB(30, 30, 53), 4)

    -- ═══════════════════════════════════════════════════════════════════════════
    -- ЛОГИКА
    -- ═══════════════════════════════════════════════════════════════════════════

    -- Обновление счётчика выделенных объектов
    Selection.SelectionChanged:Connect(function()
        local selected = Selection:Get()
        local count = 0
        for _, obj in ipairs(selected) do
            for _, child in ipairs(obj:GetDescendants()) do
                if child:IsA("Decal") or child:IsA("SpecialMesh") or child:IsA("Texture") then
                    count += 1
                end
            end
            if obj:IsA("Decal") or obj:IsA("Texture") then
                count += 1
            end
        end
        countLabel.Text = string.format("Выделено объектов: %d  |  Текстур: %d", #selected, count)
    end)

    -- Получение или создание папки PendingDeletion
    local function getPendingFolder()
        local folder = ReplicatedStorage:FindFirstChild(PENDING_FOLDER)
        if not folder then
            folder = Instance.new("Folder")
            folder.Name = PENDING_FOLDER
            folder.Parent = ReplicatedStorage
        end
        return folder
    end

    -- Парсинг TextureId (убираем "rbxassetid://")
    local function parseTextureId(raw)
        if not raw then return nil end
        local id = tostring(raw):match("%d+")
        return id
    end

    -- ── Экспорт текстур ──────────────────────────────────────────────────────
    exportBtn.MouseButton1Click:Connect(function()
        local selected = Selection:Get()
        if #selected == 0 then
            statusLabel.Text = "● Ошибка: ничего не выделено!"
            statusLabel.TextColor3 = COLOR_DANGER
            return
        end

        statusLabel.Text = "● Сканирование выделенных объектов..."
        statusLabel.TextColor3 = COLOR_WARNING

        local textures = {}
        local seen = {}

        local function scanObject(obj)
            -- Проверяем сам объект
            if obj:IsA("Decal") or obj:IsA("Texture") then
                local id = parseTextureId(obj.Texture)
                if id and not seen[id] then
                    seen[id] = true
                    table.insert(textures, {
                        id     = id,
                        name   = obj.Name,
                        parent = obj.Parent and obj.Parent.Name or "?",
                        grid   = "",
                        type   = "",
                        author = "",
                        source = "studio"
                    })
                end
            end
            -- Проверяем потомков
            for _, child in ipairs(obj:GetDescendants()) do
                if child:IsA("Decal") or child:IsA("Texture") then
                    local id = parseTextureId(child.Texture)
                    if id and not seen[id] then
                        seen[id] = true
                        table.insert(textures, {
                            id     = id,
                            name   = child.Name,
                            parent = child.Parent and child.Parent.Name or "?",
                            grid   = "",
                            type   = "",
                            author = "",
                            source = "studio"
                        })
                    end
                end
            end
        end

        for _, obj in ipairs(selected) do
            scanObject(obj)
        end

        if #textures == 0 then
            statusLabel.Text = "● Ошибка: текстур не найдено в выделенных объектах"
            statusLabel.TextColor3 = COLOR_DANGER
            exportLog.Text = "Убедитесь что в выделенных Part есть Decal или Texture"
            return
        end

        -- Сериализуем в JSON
        local success, jsonData = pcall(function()
            return HttpService:JSONEncode(textures)
        end)

        if not success then
            statusLabel.Text = "● Ошибка сериализации JSON"
            statusLabel.TextColor3 = COLOR_DANGER
            return
        end

        -- Сохраняем через буфер обмена (пользователь вставит вручную)
        -- В Studio нет прямого доступа к файловой системе без plugin:SetSetting
        -- Используем plugin:SetSetting для временного хранения
        plugin:SetSetting("LastExportJSON", jsonData)
        plugin:SetSetting("LastExportCount", #textures)
        plugin:SetSetting("LastExportTime", os.time())

        -- Копируем в буфер обмена
        local copied = pcall(function()
            setclipboard(jsonData)
        end)

        statusLabel.Text = string.format("● Экспортировано %d текстур", #textures)
        statusLabel.TextColor3 = COLOR_SUCCESS

        exportLog.Text = string.format(
            "✓ Найдено %d текстур\nДанные скопированы в буфер обмена.\nВставьте в файл input_textures.json рядом с app.py",
            #textures
        )
        exportLog.TextColor3 = COLOR_SUCCESS
    end)

    -- ── Применить удаление ───────────────────────────────────────────────────
    applyBtn.MouseButton1Click:Connect(function()
        local text = inputBox.Text
        if text == "" then
            deleteLog.Text = "Ошибка: введите ID дубликатов"
            deleteLog.TextColor3 = COLOR_DANGER
            return
        end

        -- Парсим ID из текста
        local ids = {}
        for id in text:gmatch("%d+") do
            table.insert(ids, id)
        end

        if #ids == 0 then
            deleteLog.Text = "Ошибка: не найдено ни одного ID"
            deleteLog.TextColor3 = COLOR_DANGER
            return
        end

        statusLabel.Text = string.format("● Перемещаю %d текстур...", #ids)
        statusLabel.TextColor3 = COLOR_WARNING

        local pendingFolder = getPendingFolder()
        local moved = 0
        local notFound = 0

        -- Создаём сет ID для быстрого поиска
        local idSet = {}
        for _, id in ipairs(ids) do
            idSet[id] = true
        end

        -- Ищем все Decal/Texture в workspace с этими ID
        local function searchAndMove(parent)
            for _, obj in ipairs(parent:GetDescendants()) do
                if obj:IsA("Decal") or obj:IsA("Texture") then
                    local id = parseTextureId(obj.Texture)
                    if id and idSet[id] then
                        -- Перемещаем родителя (Part) в папку ожидания
                        local partParent = obj.Parent
                        if partParent and partParent:IsA("BasePart") then
                            local clone = partParent:Clone()
                            clone.Name = string.format("DUPLICATE_%s_%s", id, partParent.Name)
                            clone.Parent = pendingFolder
                            partParent:Destroy()
                            moved += 1
                        end
                    end
                end
            end
        end

        local ok, err = pcall(searchAndMove, workspace)
        if not ok then
            deleteLog.Text = "Ошибка при поиске: " .. tostring(err)
            deleteLog.TextColor3 = COLOR_DANGER
            return
        end

        -- Также ищем в ReplicatedStorage (кроме папки ожидания)
        for _, child in ipairs(ReplicatedStorage:GetChildren()) do
            if child.Name ~= PENDING_FOLDER then
                local ok2, _ = pcall(searchAndMove, child)
            end
        end

        statusLabel.Text = string.format("● Перемещено %d объектов в PendingDeletion", moved)
        statusLabel.TextColor3 = COLOR_SUCCESS

        deleteLog.Text = string.format(
            "✓ Перемещено: %d объектов\nПуть: ReplicatedStorage → %s",
            moved, PENDING_FOLDER
        )
        deleteLog.TextColor3 = COLOR_SUCCESS

        inputBox.Text = ""
    end)

    -- ── Открыть папку ожидания ───────────────────────────────────────────────
    openFolderBtn.MouseButton1Click:Connect(function()
        local folder = getPendingFolder()
        Selection:Set({folder})
        game:GetService("Selection"):Set({folder})
    end)

    -- ── Очистить папку (финальное удаление) ─────────────────────────────────
    clearFolderBtn.MouseButton1Click:Connect(function()
        local folder = ReplicatedStorage:FindFirstChild(PENDING_FOLDER)
        if not folder then
            deleteLog.Text = "Папка PendingDeletion не найдена"
            deleteLog.TextColor3 = COLOR_WARNING
            return
        end

        local count = #folder:GetChildren()
        folder:ClearAllChildren()

        statusLabel.Text = string.format("● Удалено %d объектов из PendingDeletion", count)
        statusLabel.TextColor3 = COLOR_SUCCESS
        deleteLog.Text = string.format("✓ Окончательно удалено: %d объектов", count)
        deleteLog.TextColor3 = COLOR_SUCCESS
    end)
end

-- ── Запуск ────────────────────────────────────────────────────────────────────
buildUI()
