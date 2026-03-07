(function () {
    const configNode = document.getElementById("rule-builder-config")
    const builderRoot = document.querySelector("[data-rule-builder]")

    if (!configNode || !builderRoot) {
        return
    }

    const config = JSON.parse(configNode.textContent)
    const fields = config.fields || []
    const fieldMap = new Map(fields.map((field) => [field.name, field]))
    const fieldNames = new Set(fields.map((field) => field.name))

    const calculationExpression = document.getElementById("id_calculation_expression")
    const visibilityExpression = document.getElementById("id_visibility_condition")
    const validationExpression = document.getElementById("id_validation_expression")
    const calculationToggle = document.getElementById("id_is_calculated")
    const fieldTypeSelect = document.getElementById("id_field_type")
    const choicesTextarea = document.getElementById("id_choices_text")

    const previewNodes = {
        calculation: builderRoot.querySelector('[data-rule-preview="calculation"]'),
        visibility: builderRoot.querySelector('[data-rule-preview="visibility"]'),
        validation: builderRoot.querySelector('[data-rule-preview="validation"]'),
    }

    const calculationControls = {
        left: builderRoot.querySelector("[data-calc-left]"),
        operator: builderRoot.querySelector("[data-calc-operator]"),
        rightMode: builderRoot.querySelector("[data-calc-right-mode]"),
        rightField: builderRoot.querySelector("[data-calc-right-field]"),
        rightFieldWrap: builderRoot.querySelector("[data-calc-right-field-wrap]"),
        rightValue: builderRoot.querySelector("[data-calc-right-value]"),
        rightValueWrap: builderRoot.querySelector("[data-calc-right-value-wrap]"),
    }

    const comparisonControls = {
        visibility: {
            left: builderRoot.querySelector('[data-compare-left="visibility"]'),
            operator: builderRoot.querySelector('[data-compare-operator="visibility"]'),
            mode: builderRoot.querySelector('[data-compare-mode="visibility"]'),
            rightField: builderRoot.querySelector('[data-compare-right-field="visibility"]'),
            rightFieldWrap: builderRoot.querySelector('[data-compare-right-field-wrap="visibility"]'),
            literalWrap: builderRoot.querySelector('[data-compare-literal-wrap="visibility"]'),
            literal: builderRoot.querySelector('[data-compare-literal="visibility"]'),
            choice: builderRoot.querySelector('[data-compare-choice="visibility"]'),
            bool: builderRoot.querySelector('[data-compare-bool="visibility"]'),
        },
        validation: {
            operator: builderRoot.querySelector('[data-compare-operator="validation"]'),
            mode: builderRoot.querySelector('[data-compare-mode="validation"]'),
            rightField: builderRoot.querySelector('[data-compare-right-field="validation"]'),
            rightFieldWrap: builderRoot.querySelector('[data-compare-right-field-wrap="validation"]'),
            literalWrap: builderRoot.querySelector('[data-compare-literal-wrap="validation"]'),
            literal: builderRoot.querySelector('[data-compare-literal="validation"]'),
            choice: builderRoot.querySelector('[data-compare-choice="validation"]'),
            bool: builderRoot.querySelector('[data-compare-bool="validation"]'),
        },
    }

    function setHidden(node, hidden) {
        if (node) {
            node.hidden = hidden
        }
    }

    function setOptions(select, options, selectedValue) {
        if (!select) {
            return
        }
        const currentValue = selectedValue !== undefined ? selectedValue : select.value
        select.innerHTML = ""
        for (const option of options) {
            const element = document.createElement("option")
            element.value = option.value
            element.textContent = option.label
            if (option.value === currentValue) {
                element.selected = true
            }
            select.appendChild(element)
        }
        if (!select.value && options.length) {
            select.value = options[0].value
        }
    }

    function fieldOptions(includePlaceholder) {
        const options = []
        if (includePlaceholder) {
            options.push({ value: "", label: "Select a field" })
        }
        for (const field of fields) {
            options.push({
                value: field.name,
                label: `${field.label} (${field.name})`,
            })
        }
        if (!options.length) {
            options.push({ value: "", label: "No other fields yet" })
        }
        return options
    }

    function choiceOptionsFromTextarea() {
        if (!choicesTextarea) {
            return []
        }
        return choicesTextarea.value
            .split("\n")
            .map((value) => value.trim())
            .filter(Boolean)
    }

    function quoteLiteral(value, fieldType) {
        if (value === null || value === undefined || value === "") {
            return null
        }
        if (fieldType === "boolean") {
            return value === "true" ? "True" : "False"
        }
        if (fieldType === "integer" || fieldType === "decimal") {
            return String(value)
        }
        return JSON.stringify(String(value))
    }

    function activeLiteralControl(controls, fieldType, choices) {
        setHidden(controls.literal, true)
        setHidden(controls.choice, true)
        setHidden(controls.bool, true)

        if (fieldType === "boolean") {
            setHidden(controls.bool, false)
            return controls.bool
        }
        if (fieldType === "choice" && choices.length) {
            setOptions(
                controls.choice,
                choices.map((choice) => ({ value: choice, label: choice })),
            )
            setHidden(controls.choice, false)
            return controls.choice
        }

        controls.literal.type =
            fieldType === "integer" || fieldType === "decimal"
                ? "number"
                : fieldType === "date"
                  ? "date"
                  : "text"
        controls.literal.step = fieldType === "integer" ? "1" : "0.01"
        setHidden(controls.literal, false)
        return controls.literal
    }

    function updateCalculationComposer() {
        const literalMode = calculationControls.rightMode.value === "literal"
        setHidden(calculationControls.rightFieldWrap, literalMode)
        setHidden(calculationControls.rightValueWrap, !literalMode)
    }

    function updateComparisonComposer(kind) {
        const controls = comparisonControls[kind]
        const fieldType =
            kind === "validation"
                ? fieldTypeSelect?.value || "short_text"
                : fieldMap.get(controls.left.value)?.field_type || "short_text"
        const choices =
            kind === "validation" && fieldType === "choice"
                ? choiceOptionsFromTextarea()
                : fieldMap.get(controls.left?.value || "")?.choices || []
        const fieldMode = controls.mode.value === "field"
        setHidden(controls.rightFieldWrap, !fieldMode)
        setHidden(controls.literalWrap, fieldMode)
        if (!fieldMode) {
            activeLiteralControl(controls, fieldType, choices)
        }
    }

    function setPreview(kind, value, emptyMessage) {
        const node = previewNodes[kind]
        if (!node) {
            return
        }
        node.textContent = value && value.trim() ? value : emptyMessage
    }

    function parseLiteralToken(token) {
        const value = token.trim()
        if (!value) {
            return null
        }
        if (/^-?\d+(?:\.\d+)?$/.test(value)) {
            return { mode: "literal", value }
        }
        if (value === "True" || value === "False") {
            return { mode: "literal", value: value === "True" ? "true" : "false", fieldType: "boolean" }
        }
        if (
            (value.startsWith('"') && value.endsWith('"')) ||
            (value.startsWith("'") && value.endsWith("'"))
        ) {
            return {
                mode: "literal",
                value: value.slice(1, -1),
                fieldType: "short_text",
            }
        }
        if (fieldNames.has(value)) {
            return { mode: "field", value }
        }
        return null
    }

    function hydrateCalculationFromExpression() {
        if (!calculationExpression?.value) {
            setPreview("calculation", "", "No formula yet.")
            return
        }
        setPreview("calculation", calculationExpression.value, "No formula yet.")
        const match = calculationExpression.value.match(
            /^\s*([A-Za-z_][A-Za-z0-9_]*)\s*([+\-*/])\s*([A-Za-z_][A-Za-z0-9_]*|-?\d+(?:\.\d+)?)\s*$/,
        )
        if (!match) {
            return
        }
        const [, left, operator, right] = match
        if (!fieldNames.has(left)) {
            return
        }
        calculationControls.left.value = left
        calculationControls.operator.value = operator
        if (fieldNames.has(right)) {
            calculationControls.rightMode.value = "field"
            calculationControls.rightField.value = right
        } else {
            calculationControls.rightMode.value = "literal"
            calculationControls.rightValue.value = right
        }
        updateCalculationComposer()
    }

    function hydrateComparisonFromExpression(kind, textarea, leftMode) {
        if (!textarea?.value) {
            setPreview(
                kind,
                "",
                kind === "visibility" ? "Always visible." : "No validation yet.",
            )
            return
        }
        setPreview(
            kind,
            textarea.value,
            kind === "visibility" ? "Always visible." : "No validation yet.",
        )
        const match = textarea.value.match(
            /^\s*(value|[A-Za-z_][A-Za-z0-9_]*)\s*(==|!=|>=|<=|>|<)\s*(.+?)\s*$/,
        )
        if (!match) {
            return
        }
        const [, left, operator, right] = match
        const controls = comparisonControls[kind]
        if (leftMode === "field" && fieldNames.has(left)) {
            controls.left.value = left
        }
        controls.operator.value = operator
        const parsedRight = parseLiteralToken(right)
        if (!parsedRight) {
            return
        }
        controls.mode.value = parsedRight.mode
        if (parsedRight.mode === "field") {
            controls.rightField.value = parsedRight.value
        } else {
            updateComparisonComposer(kind)
            if (parsedRight.fieldType === "boolean") {
                controls.bool.value = parsedRight.value
            } else if (controls.choice && !controls.choice.hidden) {
                controls.choice.value = parsedRight.value
            } else {
                controls.literal.value = parsedRight.value
            }
        }
        updateComparisonComposer(kind)
    }

    function buildCalculationExpression() {
        const left = calculationControls.left.value
        const operator = calculationControls.operator.value
        if (!left) {
            return null
        }
        const right =
            calculationControls.rightMode.value === "field"
                ? calculationControls.rightField.value
                : calculationControls.rightValue.value
        if (!right) {
            return null
        }
        return `${left} ${operator} ${right}`
    }

    function buildComparisonExpression(kind) {
        const controls = comparisonControls[kind]
        const left = kind === "validation" ? "value" : controls.left.value
        if (!left) {
            return null
        }
        const operator = controls.operator.value
        let right = null
        if (controls.mode.value === "field") {
            right = controls.rightField.value
        } else if (!controls.bool.hidden) {
            right = quoteLiteral(controls.bool.value, "boolean")
        } else if (!controls.choice.hidden) {
            right = quoteLiteral(controls.choice.value, "choice")
        } else {
            const fieldType =
                kind === "validation"
                    ? fieldTypeSelect?.value || "short_text"
                    : fieldMap.get(controls.left.value)?.field_type || "short_text"
            right = quoteLiteral(controls.literal.value, fieldType)
        }
        if (!right) {
            return null
        }
        return `${left} ${operator} ${right}`
    }

    function applyRule(kind) {
        if (kind === "calculation") {
            const expression = buildCalculationExpression()
            if (!expression || !calculationExpression) {
                setPreview("calculation", "", "Complete the formula controls first.")
                return
            }
            calculationExpression.value = expression
            if (calculationToggle) {
                calculationToggle.checked = true
            }
            setPreview("calculation", expression, "No formula yet.")
            return
        }

        const target = kind === "visibility" ? visibilityExpression : validationExpression
        const emptyMessage = kind === "visibility" ? "Always visible." : "No validation yet."
        const expression = buildComparisonExpression(kind)
        if (!expression || !target) {
            setPreview(kind, "", "Complete the rule controls first.")
            return
        }
        target.value = expression
        setPreview(kind, expression, emptyMessage)
    }

    function clearRule(kind) {
        const target =
            kind === "calculation"
                ? calculationExpression
                : kind === "visibility"
                  ? visibilityExpression
                  : validationExpression
        if (target) {
            target.value = ""
        }
        if (kind === "calculation" && calculationToggle) {
            calculationToggle.checked = false
        }
        setPreview(
            kind,
            "",
            kind === "calculation"
                ? "No formula yet."
                : kind === "visibility"
                  ? "Always visible."
                  : "No validation yet.",
        )
    }

    setOptions(calculationControls.left, fieldOptions(true))
    setOptions(calculationControls.rightField, fieldOptions(true))
    setOptions(comparisonControls.visibility.left, fieldOptions(true))
    setOptions(comparisonControls.visibility.rightField, fieldOptions(true))
    setOptions(comparisonControls.validation.rightField, fieldOptions(true))

    updateCalculationComposer()
    updateComparisonComposer("visibility")
    updateComparisonComposer("validation")

    hydrateCalculationFromExpression()
    hydrateComparisonFromExpression("visibility", visibilityExpression, "field")
    hydrateComparisonFromExpression("validation", validationExpression, "value")

    calculationControls.rightMode?.addEventListener("change", updateCalculationComposer)
    comparisonControls.visibility.mode?.addEventListener("change", function () {
        updateComparisonComposer("visibility")
    })
    comparisonControls.visibility.left?.addEventListener("change", function () {
        updateComparisonComposer("visibility")
    })
    comparisonControls.validation.mode?.addEventListener("change", function () {
        updateComparisonComposer("validation")
    })
    fieldTypeSelect?.addEventListener("change", function () {
        updateComparisonComposer("validation")
    })
    choicesTextarea?.addEventListener("input", function () {
        updateComparisonComposer("validation")
    })

    for (const button of builderRoot.querySelectorAll("[data-rule-apply]")) {
        button.addEventListener("click", function () {
            applyRule(button.dataset.ruleApply)
        })
    }

    for (const button of builderRoot.querySelectorAll("[data-rule-clear]")) {
        button.addEventListener("click", function () {
            clearRule(button.dataset.ruleClear)
        })
    }

    calculationExpression?.addEventListener("input", function () {
        setPreview("calculation", calculationExpression.value, "No formula yet.")
    })
    visibilityExpression?.addEventListener("input", function () {
        setPreview("visibility", visibilityExpression.value, "Always visible.")
    })
    validationExpression?.addEventListener("input", function () {
        setPreview("validation", validationExpression.value, "No validation yet.")
    })
})()
