"""User-contributed protocol for Huawei product 2Q8M (迈睿人体存在传感器Pro 电池版).

产品: 迈睿人体存在传感器 Pro 电池版
厂商: 深圳迈睿智能科技有限公司 (Merrytek)
型号: MH3 Pro (deviceTypeId 01A, 人体感应, Mesh, uiType H5)

本适配器遵循项目规范：单品协议行为全部硬编码在本文件内，
**不跨产品复用**。2Q8M 与仓库既有 2RJB 是同厂商同系列
（2RJB = MH3，2Q8M = MH3 **Pro**），但版本不同，差异如下：

  差异点              2RJB (MH3)            2Q8M (MH3 Pro)
  ------------------  --------------------  ----------------------
  pir.status          有                    有（同）
  checkResult         诊断，App 内部逻辑    同（不映射）
  selfCheck.on        全 bundle 零引用      本机有独立"检测启动"语义
  sensitivity.*       有（gear/radarGear）  有（同）
  envNoiseMgmt.mode   不映射（诊断）        同（不映射）
  action 指令          1=重置无人 101=排除   本机新增 100=自动设置距离
  目标距离单位         设备分米(÷10)         Profile 明确 unit=cm，不再换算

因此各自独立实现，不提取公共基类，也不共享映射表。

=====================================================================
Profile 服务一览（含未映射项）
=====================================================================
  pir.status             enum R  1=有人 0=无人      -> presence (binary_sensor, motion)

  luminance.current      int  R 0~65535 lux         -> illuminance
  luminance.level        enum R 1..6 光照等级        -> illuminance_level

  battery.level          int  R 1~100 %             -> battery_level
  battery.alarm          bool R 1=低电量告警         -> battery_alarm

  targetDistance.distance int R 0~65535 cm          -> target_distance

  deviceSwitch.on        bool RW 设备开关            -> device_switch
  ledSwitch.on           bool RW LED指示灯开关        -> led_switch
  indicator.indicator    bool RW LED灯语开关          -> indicator (检测到人闪一次)
  envNoiseMgmt.autoAntiInterference bool RW 环境自学习 -> auto_anti_interference

  sensitivity.gear       enum RW 0=高 1=中 2=低       -> trigger_sensitivity
  sensitivity.radarGear  enum RW 0=高 1=中 2=低       -> radar_sensitivity
  detectionPara.cfgMode  enum RW 0=普通 1=极客         -> config_mode
  detectionPara.triggerDistance   int RW 100~600 step50 cm -> trigger_distance (m)
  detectionPara.detectionDistance int RW 100~400 step50 cm -> detection_distance (m)
  delayTime.time         int  RW 20~180 s             -> absence_delay (s)

  action.action          enum RW 1=重置无人状态        -> button 重置无人状态
  action.action          enum RW 101=排除干扰          -> button 排除干扰

  checkResult.status     enum R 1=已连接 2=未连接      不映射（App 内部逻辑门）
  envNoiseMgmt.mode      enum R 1=学习完成/100=失败/101=学习中
                                                     不映射为实体，见下方说明
  envNoiseMgmt.disturbanceDist int R 0~255 干扰物位图  不映射（见下方说明）
  update.*               OTA 全流程                   不映射（与其它适配器一致）

=====================================================================
距离单位：本机 Profile 明确 unit=cm，直接按 Profile 输出
=====================================================================
2RJB 的适配器需要把设备上报的"分米"除以 10（依据是厂商 H5 bundle 中
`triggerDistance = 10 * distance` 的写入点）。**本机 Profile 对
targetDistance.distance 明确声明 unit="cm"，triggerDistance 与
detectionDistance 也都声明 unit="cm"**，因此不再做任何隐含换算。

两个可调距离在 HA 侧以**米**呈现（min/max 换算自 Profile 的 cm 值，
步进 50cm = 0.5m），因为按米配置比按厘米直观；写入时再换算回 cm，
并严格按 Profile 的 50cm 步进对齐。

=====================================================================
为什么不映射 envNoiseMgmt.mode / disturbanceDist
=====================================================================
1. mode（1=学习完成 / 100=学习失败 / 101=正在学习）是环境自学习的
   **过程态**，只在 App 的自学习流程页内有意义。本机没有"启动学习"
   的可写入口（该服务下唯一的可写字段是 autoAntiInterference 开关），
   因此这个只读过程态在 HA 里会长期停在"学习完成"或空值，无实际价值。
   若不映射让你少一个诊断项，可随时要求补上。

2. disturbanceDist 是**按 bit 编码的距离位图**（Profile 原文：
   "bit0：0~50cm范围内有干扰物；bit1：51~100cm范围内有干扰物；
   以此类推，最大可以使用到bit7"）。原样输出 0~255 对用户没有可读性；
   若要做成有意义的实体，需要拆成 8 个二进制位（对应 8 个距离区间）
   或一个文本摘要。这属于"额外的投影决策"，在无真机样本前不臆造，
   故不映射。

3. checkResult.status（已连接/未连接）是 App 自检流程的内部逻辑门，
   从未在界面上呈现，与 2RJB 的处理保持一致，不映射。

=====================================================================
关于 selfCheck.on（检测启动）
=====================================================================
本机 Profile 有该服务：``0=完成自检 / 1=开始自检``，attrName 写作
"自动设置距离"。它是一次性触发动作（触发后设备自动测距并回写
triggerDistance），**不是持续状态**。因此按 button 语义处理更合适；
但 Profile 把 method 声明为 RW、characteristicType 为 bool，
且没有独立的状态回报字段能确认自检是否结束（checkResult 是连接
检查，不是自检结果）。**在无法确认写入效果的情况下，按失败关闭
原则暂不暴露该命令**，仅在此记录。真机验证后可补 button。

=====================================================================
报文类型（沿用 2MZN 的实测教训）
=====================================================================
Profile 的 enumList 里 ``enumVal`` 一律是**字符串**（如 ``"1"``），
但 characteristicType 是 bool/enum/int，真机只接受**数值**。
直接把枚举字符串当报文值发送会被云端拒绝（errcode=16001）。
因此本文件所有写命令都经 _coerce() 按 characteristicType 数值化，
取值本身从 Profile 的 enumList 读取，不硬编码。

=====================================================================
尚未验证（需真机确认）
=====================================================================
[ ] 状态读取：全部字段未在真机实测，仅依据 Profile 权限/枚举推导。
[ ] 控制命令：4 个 switch、2 个 select、3 个 number、2 个 button 未实测。
[ ] **pir.status 的清除行为**：本设备是"人体存在"传感器（雷达），
    理论上会持续上报有人/无人两个状态（不同于摄像头的告警一次性信号）。
    若真机实测发现无人状态不上报（长期停在"有人"），需改为
    event/告警式处理（参照 prod_2gaf.py 的做法）。
[ ] 动作指令 action=1（重置无人状态）与 action=101（排除干扰）的
    生效时间与可观测结果未验证（写入后没有直接的状态回报字段）。
[ ] 距离参数：min/max 取自 Profile（trigger 100~600cm、
    detection 100~400cm、步进 50cm）。若真机实际范围不同需修正。
[ ] 无人检测延时 20~180s 是否为线性可调（还是有预设档位）未验证。
[ ] 光照等级 level 的 6 档中文标签直接取自 Profile 的 descCh，
    但 Profile 的 descCh 与 descEn 的区间描述互相矛盾
    （如 descEn 说 Dark 是 0~50，descCh 说暗光是 0~10）。
    本适配器采用 descCh（中文，与 App 显示一致）。若真机对不上，
    应以 luminance.current 的实际 lux 读数为准。
[ ] battery.level 的实际上报频率未验证（电池设备可能为省电降频）。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .api import EntitySpec
from .context import DeviceContext

# --- 服务/字段常量（本机 Profile，不与 2RJB 共享） -------------------
_PIR_SID = "pir"
_PIR_FIELD = "status"

_LUMI_SID = "luminance"
_LUMI_CURRENT = "current"
_LUMI_LEVEL = "level"

_BATTERY_SID = "battery"
_BATTERY_LEVEL = "level"
_BATTERY_ALARM = "alarm"

_TARGET_SID = "targetDistance"
_TARGET_FIELD = "distance"

_DETECTION_SID = "detectionPara"
_CFG_MODE = "cfgMode"
_TRIGGER_FIELD = "triggerDistance"
_DETECTION_FIELD = "detectionDistance"

_DELAY_SID = "delayTime"
_DELAY_FIELD = "time"

_SENSITIVITY_SID = "sensitivity"
_SENS_GEAR = "gear"
_SENS_RADAR = "radarGear"

_NOISE_SID = "envNoiseMgmt"
_NOISE_AUTO = "autoAntiInterference"

_ACTION_SID = "action"
_ACTION_FIELD = "action"
_ACTION_RESET_ABSENCE = 1
_ACTION_EXCLUDE_INTERFERENCE = 101

_CM_PER_M = 100

# 灵敏度枚举（本机两处共用同一刻度）：0=高 1=中 2=低
_GEAR_OPTIONS = ((0, "高"), (1, "中"), (2, "低"))

# 配置模式：0=普通模式 1=极客模式
_CFG_MODE_OPTIONS = ((0, "普通模式"), (1, "极客模式"))

# 光照等级：标签取自本机 Profile 的 descCh。
_LIGHT_LEVEL_LABELS = {
    1: "暗光(0～10)",
    2: "微光(11～20)",
    3: "弱光(21～30)",
    4: "适中(31～300)",
    5: "较强(301～500)",
    6: "很强(501以上)",
}


# ---------------------------------------------------------------------
# 取值解码
# ---------------------------------------------------------------------
def _bool(value: Any) -> bool | None:
    """Decode a Huawei bool/enum characteristic into a Python bool."""

    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value.strip().casefold() in {"1", "true", "on"}:
            return True
        if value.strip().casefold() in {"0", "false", "off"}:
            return False
        return None
    if isinstance(value, (int, float)):
        return bool(value)
    return None


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value: Any) -> int | None:
    number = _number(value)
    return None if number is None else int(round(number))


def _text(value: Any) -> str | None:
    """Return a non-empty string, otherwise ``None``."""

    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


# ---------------------------------------------------------------------
# Profile 读取与报文编码
# ---------------------------------------------------------------------
def _field(
    profile: Mapping[str, Any] | None,
    sid: str,
    name: str,
) -> Mapping[str, Any] | None:
    """Return one Profile characteristic definition, if declared."""

    if not isinstance(profile, Mapping):
        return None
    for service in profile.get("services", ()):
        if not isinstance(service, Mapping) or service.get("serviceId") != sid:
            continue
        for field in service.get("characteristics", ()):
            if (
                isinstance(field, Mapping)
                and field.get("characteristicName") == name
            ):
                return field
        return None
    return None


def _is_writable(field: Mapping[str, Any] | None) -> bool:
    """Return whether the Profile declares a write capability."""

    if not isinstance(field, Mapping):
        return False
    return "W" in str(field.get("method") or "")


def _coerce(value: Any, field: Mapping[str, Any] | None) -> Any:
    """Encode a command value using the Profile-declared characteristic type.

    Profile 的 enumList 里 enumVal 是字符串，但 bool/enum/int 类字段
    真机只接受数值（否则云端回 errcode=16001）。此处统一数值化。
    """

    if not isinstance(field, Mapping):
        return value
    data_type = str(field.get("characteristicType") or "").casefold()
    if data_type in {"bool", "int", "integer", "enum"}:
        number = _number(value)
        if number is None:
            return value
        return int(number) if number.is_integer() else number
    if data_type in {"float", "double", "number"}:
        number = _number(value)
        return value if number is None else number
    return value


def _enum_value(
    field: Mapping[str, Any] | None,
    wanted: Any,
    fallback: Any,
) -> Any:
    """Resolve the Profile-declared enum value matching ``wanted``."""

    raw: Any = fallback
    if isinstance(field, Mapping):
        for option in field.get("enumList", ()):
            if not isinstance(option, Mapping):
                continue
            candidate = option.get("enumVal")
            if candidate is None:
                continue
            if str(candidate) == str(wanted):
                raw = candidate
                break
            if str(wanted) in {
                str(option.get("descCh") or ""),
                str(option.get("descEn") or ""),
            }:
                raw = candidate
                break
    return _coerce(raw, field)


def _clamp(value: Any, field: Mapping[str, Any] | None) -> Any:
    """Clamp a numeric write to the Profile range and align to its step."""

    number = _number(value)
    if number is None:
        return None
    minimum = _number((field or {}).get("min"))
    maximum = _number((field or {}).get("max"))
    if minimum is not None and maximum is not None and maximum < minimum:
        minimum, maximum = maximum, minimum
    if minimum is not None:
        number = max(number, minimum)
    if maximum is not None:
        number = min(number, maximum)
    step = _number((field or {}).get("step"))
    if step is None or step <= 0:
        data_type = str((field or {}).get("characteristicType") or "").casefold()
        step = 1.0 if data_type in {"int", "integer", "enum", "bool"} else None
    if step:
        base = minimum if minimum is not None else 0.0
        number = base + round((number - base) / step) * step
        if minimum is not None:
            number = max(number, minimum)
        if maximum is not None:
            number = min(number, maximum)
    return _coerce(round(number, 4), field)


def _enum_label(field: Mapping[str, Any] | None, value: Any) -> str | None:
    """Resolve a reported raw value to its Profile label."""

    if not isinstance(field, Mapping) or value is None:
        return None
    for option in field.get("enumList", ()):
        if not isinstance(option, Mapping):
            continue
        if str(option.get("enumVal")) != str(value):
            continue
        label = option.get("descCh") or option.get("descEn")
        if isinstance(label, str) and label.strip():
            return label.strip()
    return None


# ---------------------------------------------------------------------
# 实体构造
# ---------------------------------------------------------------------
def _make_switch(
    context: DeviceContext,
    sid: str,
    field_name: str,
    key: str,
    name: str,
) -> EntitySpec:
    field = _field(context.profile, sid, field_name)
    on_value = _enum_value(field, 1, 1)
    off_value = _enum_value(field, 0, 0)

    async def turn_on(device: DeviceContext, _data: Mapping[str, Any]) -> None:
        await device.async_send_service(sid, {field_name: on_value})

    async def turn_off(device: DeviceContext, _data: Mapping[str, Any]) -> None:
        await device.async_send_service(sid, {field_name: off_value})

    return EntitySpec(
        platform="switch",
        key=key,
        name=name,
        state=lambda device: {"is_on": _bool(device.value(sid, field_name))},
        actions={"turn_on": turn_on, "turn_off": turn_off},
    )


def _make_select(
    context: DeviceContext,
    sid: str,
    field_name: str,
    key: str,
    name: str,
    options: tuple[tuple[int, str], ...],
) -> EntitySpec:
    field = _field(context.profile, sid, field_name)
    labels = tuple(label for _, label in options)
    by_label = {label: raw for raw, label in options}
    by_raw = {str(raw): label for raw, label in options}

    def state(device: DeviceContext) -> Mapping[str, Any]:
        raw = _int(device.value(sid, field_name))
        if raw is None:
            return {"current_option": None}
        return {"current_option": by_raw.get(str(raw))}

    async def select(device: DeviceContext, data: Mapping[str, Any]) -> None:
        wanted = str(data.get("option"))
        raw = by_label.get(wanted)
        if raw is None:
            raise ValueError(f"unsupported option for {sid}.{field_name}: {wanted}")
        await device.async_send_service(
            sid, {field_name: _enum_value(field, raw, raw)}
        )

    return EntitySpec(
        platform="select",
        key=key,
        name=name,
        state=state,
        metadata={"options": labels},
        actions={"select_option": select},
    )


def _make_number_metres(
    context: DeviceContext,
    sid: str,
    field_name: str,
    key: str,
    name: str,
) -> EntitySpec | None:
    """A centimetre-valued Profile field exposed to HA in metres."""

    field = _field(context.profile, sid, field_name)
    if field is None:
        return None
    minimum = _number(field.get("min"))
    maximum = _number(field.get("max"))
    step = _number(field.get("step"))
    if minimum is None or maximum is None:
        return None
    if maximum < minimum:
        minimum, maximum = maximum, minimum
    step_cm = step if step and step > 0 else 1.0

    async def set_value(device: DeviceContext, data: Mapping[str, Any]) -> None:
        metres = _number(data.get("value"))
        if metres is None:
            return
        # 米 -> 厘米，再按 Profile 的范围与步进夹取对齐。
        value = _clamp(round(metres * _CM_PER_M, 4), field)
        if value is None:
            return
        await device.async_send_service(sid, {field_name: value})

    def state(device: DeviceContext) -> Mapping[str, Any]:
        raw = _number(device.value(sid, field_name))
        return {"native_value": None if raw is None else raw / _CM_PER_M}

    return EntitySpec(
        platform="number",
        key=key,
        name=name,
        state=state,
        metadata={
            "min": minimum / _CM_PER_M,
            "max": maximum / _CM_PER_M,
            "step": step_cm / _CM_PER_M,
            "unit": "m",
        },
        actions={"set_value": set_value},
    )


def _make_number_seconds(
    context: DeviceContext,
    sid: str,
    field_name: str,
    key: str,
    name: str,
) -> EntitySpec | None:
    """A seconds-valued Profile field exposed as a plain number."""

    field = _field(context.profile, sid, field_name)
    if field is None:
        return None
    minimum = _number(field.get("min"))
    maximum = _number(field.get("max"))
    step = _number(field.get("step"))

    async def set_value(device: DeviceContext, data: Mapping[str, Any]) -> None:
        value = _clamp(data.get("value"), field)
        if value is None:
            return
        await device.async_send_service(sid, {field_name: value})

    def state(device: DeviceContext) -> Mapping[str, Any]:
        return {"native_value": _number(device.value(sid, field_name))}

    return EntitySpec(
        platform="number",
        key=key,
        name=name,
        state=state,
        metadata={
            "min": minimum if minimum is not None else 0,
            "max": maximum if maximum is not None else 100,
            "step": step if step and step > 0 else 1,
            "unit": "s",
        },
        actions={"set_value": set_value},
    )


def _make_sensor(
    sid: str,
    field_name: str,
    key: str,
    name: str,
    *,
    unit: str | None = None,
    device_class: str | None = None,
    state_class: str | None = None,
    entity_category: str | None = None,
    decode: Any = None,
) -> EntitySpec:
    decoder = decode or (lambda value: _number(value))

    def state(device: DeviceContext) -> Mapping[str, Any]:
        return {"native_value": decoder(device.value(sid, field_name))}

    metadata: dict[str, Any] = {}
    if unit is not None:
        metadata["unit"] = unit
    if device_class is not None:
        metadata["device_class"] = device_class
    if state_class is not None:
        metadata["state_class"] = state_class
    if entity_category is not None:
        metadata["entity_category"] = entity_category

    return EntitySpec(
        platform="sensor",
        key=key,
        name=name,
        state=state,
        metadata=metadata,
    )


def _make_action_button(
    context: DeviceContext,
    value: int,
    key: str,
    name: str,
) -> EntitySpec:
    field = _field(context.profile, _ACTION_SID, _ACTION_FIELD)
    payload = _enum_value(field, value, value)

    async def press(device: DeviceContext, _data: Mapping[str, Any]) -> None:
        await device.async_send_service(_ACTION_SID, {_ACTION_FIELD: payload})

    return EntitySpec(
        platform="button",
        key=key,
        name=name,
        state=lambda device: {},
        actions={"press": press},
    )


class Product2Q8MAdapter:
    """Keep all 2Q8M entity and command choices in this file."""

    prod_id = "2Q8M"

    def entities(self, context: DeviceContext) -> tuple[EntitySpec, ...]:
        profile = context.profile
        if profile is None:
            return ()

        entities: list[EntitySpec] = []

        # --- 人体存在（核心） -----------------------------------------
        if context.has_service(_PIR_SID):
            entities.append(
                EntitySpec(
                    platform="binary_sensor",
                    key="presence",
                    name="人体存在",
                    state=lambda device: {
                        "is_on": _bool(device.value(_PIR_SID, _PIR_FIELD))
                    },
                    metadata={"device_class": "motion"},
                )
            )

        # --- 光照 -----------------------------------------------------
        if context.has_service(_LUMI_SID):
            if _field(profile, _LUMI_SID, _LUMI_CURRENT) is not None:
                entities.append(
                    _make_sensor(
                        _LUMI_SID, _LUMI_CURRENT, "illuminance", "光照度",
                        unit="lx", device_class="illuminance",
                        state_class="measurement",
                        decode=_int,
                    )
                )
            if _field(profile, _LUMI_SID, _LUMI_LEVEL) is not None:
                level_field = _field(profile, _LUMI_SID, _LUMI_LEVEL)

                def level_state(device: DeviceContext) -> Mapping[str, Any]:
                    raw = _int(device.value(_LUMI_SID, _LUMI_LEVEL))
                    if raw is None:
                        return {"native_value": None}
                    label = _enum_label(level_field, raw)
                    if label is None:
                        label = _LIGHT_LEVEL_LABELS.get(raw)
                    return {
                        "native_value": label if label is not None else raw,
                        "extra_state_attributes": {"raw_level": raw},
                    }

                entities.append(
                    EntitySpec(
                        platform="sensor",
                        key="illuminance_level",
                        name="光照等级",
                        state=level_state,
                    )
                )

        # --- 目标距离 -------------------------------------------------
        if context.has_service(_TARGET_SID) and _field(
            profile, _TARGET_SID, _TARGET_FIELD
        ) is not None:
            entities.append(
                _make_sensor(
                    _TARGET_SID, _TARGET_FIELD, "target_distance", "目标距离",
                    unit="cm", device_class="distance",
                    state_class="measurement",
                    entity_category="diagnostic",
                    decode=_int,
                )
            )

        # --- 电池 -----------------------------------------------------
        if context.has_service(_BATTERY_SID):
            if _field(profile, _BATTERY_SID, _BATTERY_LEVEL) is not None:
                entities.append(
                    _make_sensor(
                        _BATTERY_SID, _BATTERY_LEVEL, "battery_level",
                        "电池电量", unit="%", device_class="battery",
                        state_class="measurement", decode=_int,
                    )
                )
            if _field(profile, _BATTERY_SID, _BATTERY_ALARM) is not None:
                entities.append(
                    EntitySpec(
                        platform="binary_sensor",
                        key="battery_alarm",
                        name="低电量告警",
                        state=lambda device: {
                            "is_on": _bool(
                                device.value(_BATTERY_SID, _BATTERY_ALARM)
                            )
                        },
                        metadata={"device_class": "battery"},
                    )
                )

        # --- 开关 -----------------------------------------------------
        for sid, field_name, key, name in (
            ("deviceSwitch", "on", "device_switch", "设备开关"),
            ("ledSwitch", "on", "led_switch", "LED指示灯"),
            ("indicator", "indicator", "indicator_flash", "LED灯语"),
            (_NOISE_SID, _NOISE_AUTO, "auto_anti_interference", "环境自学习"),
        ):
            field = _field(profile, sid, field_name)
            if context.has_service(sid) and _is_writable(field):
                entities.append(
                    _make_switch(context, sid, field_name, key, name)
                )

        # --- 灵敏度 / 配置模式（select） -------------------------------
        if context.has_service(_SENSITIVITY_SID):
            if _is_writable(_field(profile, _SENSITIVITY_SID, _SENS_GEAR)):
                entities.append(
                    _make_select(
                        context, _SENSITIVITY_SID, _SENS_GEAR,
                        "trigger_sensitivity", "触发灵敏度", _GEAR_OPTIONS,
                    )
                )
            if _is_writable(_field(profile, _SENSITIVITY_SID, _SENS_RADAR)):
                entities.append(
                    _make_select(
                        context, _SENSITIVITY_SID, _SENS_RADAR,
                        "radar_sensitivity", "毫米波灵敏度", _GEAR_OPTIONS,
                    )
                )
        if context.has_service(_DETECTION_SID) and _is_writable(
            _field(profile, _DETECTION_SID, _CFG_MODE)
        ):
            entities.append(
                _make_select(
                    context, _DETECTION_SID, _CFG_MODE,
                    "config_mode", "配置模式", _CFG_MODE_OPTIONS,
                )
            )

        # --- 距离 / 延时（number） -------------------------------------
        if context.has_service(_DETECTION_SID):
            spec = _make_number_metres(
                context, _DETECTION_SID, _TRIGGER_FIELD,
                "trigger_distance", "触发距离",
            )
            if spec is not None:
                entities.append(spec)
            spec = _make_number_metres(
                context, _DETECTION_SID, _DETECTION_FIELD,
                "detection_distance", "检测距离",
            )
            if spec is not None:
                entities.append(spec)
        if context.has_service(_DELAY_SID):
            spec = _make_number_seconds(
                context, _DELAY_SID, _DELAY_FIELD,
                "absence_delay", "无人检测延时",
            )
            if spec is not None:
                entities.append(spec)

        # --- AI 指令（button） ----------------------------------------
        if context.has_service(_ACTION_SID) and _is_writable(
            _field(profile, _ACTION_SID, _ACTION_FIELD)
        ):
            entities.append(
                _make_action_button(
                    context, _ACTION_RESET_ABSENCE,
                    "reset_absence", "重置无人状态",
                )
            )
            entities.append(
                _make_action_button(
                    context, _ACTION_EXCLUDE_INTERFERENCE,
                    "exclude_interference", "排除干扰",
                )
            )

        # --- 固件版本（诊断） -----------------------------------------
        if context.has_service("update"):
            entities.append(
                _make_sensor(
                    "update", "version", "firmware_version", "固件版本",
                    entity_category="diagnostic", decode=_text,
                )
            )

        return tuple(entities)


ADAPTER = Product2Q8MAdapter()
