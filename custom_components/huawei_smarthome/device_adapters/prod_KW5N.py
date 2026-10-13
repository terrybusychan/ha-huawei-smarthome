"""User-contributed protocol for Huawei product KW5N (华为智能门锁 2 Ultra).

产品: 华为智能门锁 2 Ultra
厂商: 华为 (HUAWEI)
型号: AGS-X25 (deviceTypeId A0B, 智能门锁, WiFi, uiType PLUGIN / PART_ARKUIX)

本适配器遵循项目规范：单品协议行为全部硬编码在本文件内，
**不跨产品复用**。KW5N 与仓库既有 KW02/KW59/KW5L 等同系列门锁共享
lockStatus / event 的枚举空间，但本机 Profile 有明显差异（见下表），
故独立实现。

  差异点                 KW59 (E211)            KW5N (2 Ultra)
   --------------------  ---------------------  ----------------------
   lockStatus.status      RW                     RW（同）
   人脸识别               faces(只读列表)         securitySetting.faceIdentifySwitch
   布防 / 双重验证        无                     deploymentSwitch / doubleCheckSwitch
   身高/传感器开门          无                     enableSenserOpenSwitch
   猫眼设置               部分                   12 项（含逗留抓拍/实时视频/畸变校正/
                                                拍摄间隔/拍摄时长/呼叫有效期/侦测距离）
   告警事件订阅开关        无                     10 个 alarmEventSetting 开关
   音量设置               无                     volumeSetting（铃声/按键/语音/夜间）
   用户名单               users                  users（同）

=====================================================================
Profile 服务一览（含未映射项）
=====================================================================
  lockStatus.status        int  RW 1=门未关异常上锁 2=已开锁 3=已上锁 4=已关门 6=已反锁
                                                    -> lock + door + lock_status
  networkConnectState.state int R 0=离线 1=休眠 2=在线 -> connectivity (binary_sensor)
  doorBattery.level        int  R -1~100             -> door_battery
  catEyeBattery.level      int  R -1~100             -> cat_eye_battery
  lockAlarm.alarm          int  R 1=故障 2=低电量 3=长期未上线 -> alarm + low_battery

  event.*                  int/string R 操作与告警记录  -> event 实体（每次触发）
    eventType / userName / userOperation(34 值) /
    doorAlarmState(15 值) / recordType / alarmId / eventTime

  securitySetting.*        8 项 RW                   -> 8 个 switch
    isAuth / auth（管理员密码校验）                    不映射，见下方说明
    deploymentSwitch       布防                    -> deployment
    doubleCheckSwitch      双重验证                -> double_check
    passwordVerificationSwitch 密码验证             -> password_verification
    enableLockoutSwitch    锁定开关                -> enable_lockout
    faceIdentifySwitch     人脸识别                -> face_identify
    enableSenserOpenSwitch 传感器开门               -> sensor_open

  alarmEventSetting.*      10 开关 + 2 时间 + 2 枚举  -> 10 switch + 2 select
    doorNotCLoseSwitch / unlockSwitch / lockBrokenSwitch /
    forceUnlockedSwitch / alertModeUnlockedSwitch / lowBatterySwitch /
    takeSnapshotSwitch / doorOpenSwitch / messagePushSwitch
    outAlarmTime(3 档) / inAlarmTime(3 档)        -> 2 个 select
    messagePushTime + startTime/endTime           不映射，见下方说明

  catEyeSetting.*          5 开关 + 5 枚举 + 2 时间   -> 5 switch + 5 select
    staySnapshotSwitch / liveVideoSwitch / distortionCorrectionSwitch /
    takeSnapshotSwitch / shimmerFullColorSwitch
    stayDuration(13 档) / shootingInterval(6 档) / shootingDuration(3 档) /
    callValidPeriod(5 档) / detectDistance(3 档)
    startTime/endTime（生效时段）                  不映射，见下方说明

  volumeSetting.*          8 项                     -> 部分 switch
    nightModeSwitch        夜间模式                -> night_mode
    ringVolume/keyVolume/voiceVolume/currentRing     不映射，见下方说明
    supportedRing(只读)                             不映射（能力位图）
    startTime/endTime                               不映射（时段）

  temporaryCipher.periodicCiper  object RW 临时密码 不映射（见下方说明）
  users.userList / ciphers.cipher / faces.face /
  fingers.finger / keyCards.keyCard / watchs.watch /
  walletKeys.walletKey     object R 凭据名单          不映射（见下方说明）

  update.*                 OTA 全流程                不映射（与其它适配器一致）
  netInfo.*                网络                       -> 诊断传感器

=====================================================================
【安全第一】为什么 lock/unlock 做成"拒绝动作"
=====================================================================
本机 Profile 把 ``lockStatus.status`` 声明为 RW，因此适配器**有资格**
注册 lock / unlock 动作。但同系列门锁（KW02，见仓库既有适配器说明）
的固件行为是：**接受写入后回 errcode=0，然后立刻重新上报未改变的
状态**——即"假成功"。华为智慧生活 App 也**不提供**该系列的远程开锁。

HA 的 lock 实体无论如何都会渲染"上锁/解锁"按钮。如果适配器不注册
动作，按下会抛通用的 "adapter action is unavailable"；如果照 Profile
注册，就会向门锁发出真实指令，存在**远程开锁的安全风险**，而且很可能
是假成功（用户以为开了、其实没开，或反之）。

因此本适配器**注册显式拒绝动作**：按下按钮立即抛出可自解释的错误，
**不向门锁发送任何数据**。这既诚实又安全。

若日后真机确认该型号支持远程开锁，应把 _refusal_action 替换为实际
写入动作，并同步更新本说明。

=====================================================================
为什么不映射 temporaryCipher（临时密码）
=====================================================================
``temporaryCipher.periodicCiper`` 是 object（max 1024），properties 为
id / nm / ct / rd / st / et / act —— 其中 **ct 极可能是密码明文本身**，
且 object 里没有任何字段说明各 property 的具体格式（如 ct 的长度与
字符集、st/et 的时间格式）。

本集成没有"读-改-写"该结构的能力，而**临时密码是开门凭据**：
一旦格式构造错误，轻则失效，重则可能写入一个非预期的可用密码。
按失败关闭原则**不映射**。请在华为智慧生活 App 中管理临时密码。

=====================================================================
为什么不映射凭据名单（users/ciphers/faces/fingers/keyCards/watchs/walletKeys）
=====================================================================
这 7 个服务的 characteristic 都是 ``object``，承载"用户及其全部凭据"
的**名单**（每个元素含 uid / cp（凭据载荷）/ hj（指纹模板）等）。
它们是**凭据本体**而非状态：
  * cp / hj 是加密或模板载荷，在 HA 状态机里暴露没有用户价值；
  * 名单可能很长，逐条投影会产生大量实体并泄露家庭成员信息；
  * Profile 未声明这些 object 是单条还是数组、更新语义为何。
因此按失败关闭原则**不映射为实体**。门锁的凭据管理请使用官方 App。

=====================================================================
为什么不映射音量数值 / 时段 / 能力位图
=====================================================================
1. volumeSetting.ringVolume / keyVolume / voiceVolume / currentRing：
   Profile **只声明 int，没有 min/max/step，也没有枚举或单位**。
   取值域未知，做成 number 需要凭空假设范围（写错可能静音或爆响）。
   故不映射，仅映射语义明确的 nightModeSwitch（0/1 枚举）。
2. supportedRing：只读 int，是"支持的铃声音色"**位图/集合**，无枚举
   说明，原样输出不可读。
3. 各服务的 startTime / endTime（生效时段）与 messagePushTime
   （全天/自定义）：它们是**成组生效的时段配置**，单独暴露会产生
   "改了开始时间但结束时间没同步"这类不一致状态；且 Profile 未给
   时间串格式（maxLength 8/无说明）。按失败关闭原则不映射。
4. securitySetting.isAuth / auth：auth 是管理员密码载荷（max 400），
   isAuth 表示"是否要求携带该密码"。属于**凭据校验通道**，
   且与拒绝远程开锁的设计互相印证——不应暴露，故不映射。

=====================================================================
报文类型（沿用 2MZN 的实测教训）
=====================================================================
本机 Profile 的 ``enumList.enumVal`` 类型**不统一**：多数是 int
（如 lockStatus 的 1/2/3/4/6），但 ``update.action`` 是字符串
（"0"/"1"）。真机对 bool/enum/int 类字段只接受**数值**，直接把
枚举字符串当报文值发送会被云端拒绝（errcode=16001）。
因此本文件所有写命令都经 _coerce() 按 characteristicType 数值化。

注意本机 Profile **完全没有 permission 字段**，故不能用
_is_writable() 判断可写性，改为按 ``method`` 是否含 "W" 判断。

=====================================================================
为什么诊断实体默认不创建
=====================================================================
`netInfo`（Wi-Fi 信号格数 / RSSI / IP / SSID / BSSID）与 `update.version`
（固件版本）这 6 个实体在真机上**全部长期为 unknown** —— 设备不上报这些
读取字段，集成侧也没有别的读取路径可以拿到。

保留它们只会让设备页被一堆永远没有值的实体占满，用户还会以为是集成坏了。
因此**默认不创建**。

代码并未删除，而是收进 ``_make_diagnostic_entities()``，由模块级开关
``_ENABLE_DIAGNOSTIC_ENTITIES``（当前 False）控制。
若日后在真机上确认这些字段**确实会上报**（例如固件升级后行为改变），
把该开关改为 True 即可全部恢复，无需重新实现。

注意：开关打开后取值逻辑仍是原样——按 Profile 字段读取，不做任何猜测；
设备不上报时依然显示 unknown。这是刻意的：宁可显示 unknown，
也不给一个编造出来的网络状态。

=====================================================================
尚未验证（需真机确认）
=====================================================================
[ ] 状态读取：全部字段未在真机实测，仅依据 Profile 定义推导。
[ ] 控制命令：8 个 securitySetting switch、10 个 alarmEventSetting
    switch、5 个 catEyeSetting switch、2+5 个 select、1 个 night_mode
    switch，均未实测。
[ ] **lockStatus 的过渡值**：同系列固件会上报 Profile 未声明的值
    （KW02 观察到 7）。本适配器沿用"保留最后一个已声明状态"的做法，
    真机若上报新值需确认是否要补标签。
[ ] **门锁是否支持远程开锁**：见上方安全说明。装机后请勿依赖 HA
    的解锁按钮；请在 App 内或门锁面板操作。
[ ] doorBattery / catEyeBattery 是否实际上报未验证。同系列机型
    （AGS-E211 / KW02）**从不上报这两个服务**，电量走 Profile 未声明
    的 batteryManager。本适配器只读 Profile 声明的服务；若真机这两项
    长期为空，需要按同系列的做法补 batteryManager 回退。
[ ] lockAlarm 是否上报未验证（同系列恒为空）。当前 alarm / low_battery
    会回退到 event.doorAlarmState。
[ ] networkConnectState.state=1（休眠）在 HA connectivity 上如何呈现
    未验证；当前只有 2（在线）视为连通。
[ ] event.userOperation 的 34 个枚举与 doorAlarmState 的 15 个枚举
    是否与 App 显示一致未验证。
[ ] update.action 的字段类型是 string（"0"/"1"）而其它枚举是 int，
    写入格式未验证；本适配器不映射 OTA。
[ ] netInfo 各字段设备是否实际上报未验证（诊断类，不影响主功能）。
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta, timezone
from typing import Any

from .api import EntitySpec
from .context import DeviceContext

# 诊断实体（netInfo / update）总开关。
# 真机实测：这些实体全部为 unknown，设备不上报对应字段。
# 默认关闭以免污染界面；若日后确认真机会上报，改为 True 即可恢复。
_ENABLE_DIAGNOSTIC_ENTITIES = False


_LOGGER = logging.getLogger(__name__)

# --- 服务/字段常量 ---------------------------------------------------
_LOCK_STATUS_SID = "lockStatus"
_LOCK_STATUS_FIELD = "status"

_NET_STATE_SID = "networkConnectState"
_NET_STATE_FIELD = "state"

_DOOR_BATTERY_SID = "doorBattery"
_CAT_EYE_BATTERY_SID = "catEyeBattery"
_BATTERY_LEVEL_FIELD = "level"

_LOCK_ALARM_SID = "lockAlarm"
_LOCK_ALARM_FIELD = "alarm"

_EVENT_SID = "event"

# --- lockStatus/status 取值（本机 Profile） --------------------------
_STATUS_DOOR_AJAR_LOCKED = 1  # 门未关异常上锁
_STATUS_UNLOCKED = 2  # 已开锁
_STATUS_LOCKED = 3  # 已上锁
_STATUS_DOOR_CLOSED = 4  # 已关门
_STATUS_DEADBOLTED = 6  # 已反锁

_LOCKED_STATUSES = frozenset(
    {_STATUS_DOOR_AJAR_LOCKED, _STATUS_LOCKED, _STATUS_DEADBOLTED}
)
_UNLOCKED_STATUSES = frozenset({_STATUS_UNLOCKED, _STATUS_DOOR_CLOSED})
# 门扇本身只在语义明确的状态下判定。
_DOOR_OPEN_STATUSES = frozenset({_STATUS_DOOR_AJAR_LOCKED, _STATUS_UNLOCKED})
_DOOR_CLOSED_STATUSES = frozenset(
    {_STATUS_LOCKED, _STATUS_DOOR_CLOSED, _STATUS_DEADBOLTED}
)
# Profile 声明的全部状态值；未声明的过渡值被挡下，保持上一个已知状态。
_DECLARED_STATUSES = _LOCKED_STATUSES | _UNLOCKED_STATUSES

# --- 网络连通状态 ----------------------------------------------------
_NET_STATE_ONLINE = 2  # 在线（1=休眠 不视为连通）

# --- 电量 ------------------------------------------------------------
# doorBattery/catEyeBattery 声明 min=-1，不是真实百分比。
_BATTERY_UNKNOWN = -1

# --- 告警 ------------------------------------------------------------
_ALARM_LOW_BATTERY = 2  # 低电量告警
_NO_ALARM = "无告警"
# lockAlarm 一旦置位不会自动清除；超过该窗口的读数不再当作"当前"告警。
_ALARM_PULSE_WINDOW = timedelta(hours=12)

# --- 事件字段（本机 event 服务的扁平字段名） -------------------------
_EVENT_TYPE_FIELD = "eventType"          # 1=记录 2=告警
_EVENT_USER_NAME_FIELD = "userName"
_EVENT_OPERATION_FIELD = "userOperation"
_EVENT_DOOR_ALARM_FIELD = "doorAlarmState"
_EVENT_ALARM_ID_FIELD = "alarmId"
_EVENT_TIME_FIELD = "eventTime"

_EVENT_RECORD = 1
_EVENT_ALARM = 2

# userOperation 中代表"开锁"的取值（本机 Profile 明文列出）。
# 0=指纹 1=密码 2=人脸 3=门卡 4=手表手环 5=钱包 6=临时密码 7=物理钥匙
_UNLOCK_OPERATIONS = frozenset({0, 1, 2, 3, 4, 5, 6, 7})
# 24=门内开锁，25=反锁，26=解除反锁
_OPERATION_INDOOR_UNLOCK = 24
_INDOOR_UNLOCK_OPERATIONS = frozenset({_OPERATION_INDOOR_UNLOCK})

# --- 需要暴露为 switch 的设置项 --------------------------------------
# (sid, 字段名, key, 名称)  —— 均为 0/1 枚举
_SECURITY_SWITCHES = (
    ("securitySetting", "deploymentSwitch", "deployment", "布防"),
    ("securitySetting", "doubleCheckSwitch", "double_check", "双重验证"),
    (
        "securitySetting",
        "passwordVerificationSwitch",
        "password_verification",
        "密码验证",
    ),
    ("securitySetting", "enableLockoutSwitch", "enable_lockout", "锁定开关"),
    ("securitySetting", "faceIdentifySwitch", "face_identify", "人脸识别"),
    (
        "securitySetting",
        "enableSenserOpenSwitch",
        "sensor_open",
        "传感器开门",
    ),
)

_ALARM_EVENT_SWITCHES = (
    ("doorNotCLoseSwitch", "alarm_door_not_close", "门未关告警"),
    ("unlockSwitch", "alarm_unlock", "开锁告警"),
    ("lockBrokenSwitch", "alarm_lock_broken", "锁被破坏告警"),
    ("forceUnlockedSwitch", "alarm_force_unlocked", "强制开锁告警"),
    ("alertModeUnlockedSwitch", "alarm_alert_mode", "布防告警"),
    ("lowBatterySwitch", "alarm_low_battery", "低电量告警推送"),
    ("takeSnapshotSwitch", "alarm_snapshot", "告警抓拍"),
    ("doorOpenSwitch", "alarm_door_open", "门开告警"),
    ("messagePushSwitch", "alarm_message_push", "消息推送"),
)

_CAT_EYE_SWITCHES = (
    ("staySnapshotSwitch", "cateye_stay_snapshot", "逗留抓拍"),
    ("liveVideoSwitch", "cateye_live_video", "实时视频"),
    (
        "distortionCorrectionSwitch",
        "cateye_distortion_correction",
        "畸变校正",
    ),
    ("takeSnapshotSwitch", "cateye_snapshot", "抓拍"),
    ("shimmerFullColorSwitch", "cateye_full_color", "全彩微光"),
)

# --- 需要暴露为 select 的枚举项 --------------------------------------
# (sid, 字段名, key, 名称, 顺序)
_SELECT_SPECS = (
    ("alarmEventSetting", "outAlarmTime", "alarm_out_time", "室外告警时长",
     ("0", "1", "2")),
    ("alarmEventSetting", "inAlarmTime", "alarm_in_time", "室内告警时长",
     ("0", "1", "2")),
    ("catEyeSetting", "stayDuration", "cateye_stay_duration", "逗留时长",
     tuple(str(v) for v in range(13))),
    ("catEyeSetting", "shootingInterval", "cateye_interval", "抓拍间隔",
     ("0", "1", "2", "3", "4", "5")),
    ("catEyeSetting", "shootingDuration", "cateye_duration", "抓拍时长",
     ("0", "1", "2")),
    ("catEyeSetting", "callValidPeriod", "cateye_call_period", "呼叫有效期",
     ("0", "1", "2", "3", "4")),
    ("catEyeSetting", "detectDistance", "cateye_distance", "侦测距离",
     ("0", "1", "2")),
)

# netInfo.intensity：Profile 声明 0~100 整数（非 20/40/60/80/100 编码）。
# 但同系列其它机型用 20/40/60/80/100 五档；本机是连续 0~100，
# 因此直接按原始数值输出，不做格数换算。


# ---------------------------------------------------------------------
# 取值解码
# ---------------------------------------------------------------------
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
    """本机 Profile 没有 permission 字段，故按 method 判断可写性。"""

    if not isinstance(field, Mapping):
        return False
    return "W" in str(field.get("method") or "")


def _coerce(value: Any, field: Mapping[str, Any] | None) -> Any:
    """按 Profile 声明的 characteristicType 数值化命令取值。

    本机 enumVal 类型不统一（多为 int，update.action 是 str），
    真机对 int/enum 类字段只接受数值，故统一数值化。
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
    """只按 enumVal 精确匹配，不做 descCh/descEn 文本回退。

    文本回退会在枚举文案互相包含时命中错误档位
    （2QWL 适配中踩过的真实 bug：descEn "110" 与另一档混淆）。
    """

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
    return _coerce(raw, field)


def _enum_label(field: Mapping[str, Any] | None, value: Any) -> str | None:
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


def _enum_options(
    field: Mapping[str, Any] | None,
    order: tuple[str, ...] | None = None,
) -> tuple[tuple[Any, str], ...]:
    options: list[tuple[Any, str]] = []
    if not isinstance(field, Mapping):
        return ()
    for option in field.get("enumList", ()):
        if not isinstance(option, Mapping):
            continue
        raw = option.get("enumVal")
        if raw is None:
            continue
        label = option.get("descCh") or option.get("descEn") or str(raw)
        options.append((raw, str(label)))
    if order is not None:
        rank = {str(value): index for index, value in enumerate(order)}
        options.sort(key=lambda item: rank.get(str(item[0]), len(rank)))
    return tuple(options)


# ---------------------------------------------------------------------
# 拒绝动作（安全关键）
# ---------------------------------------------------------------------
def _refusal_action(verb: str) -> Callable[..., Any]:
    """返回一个显式拒绝的协程，**不向门锁发送任何数据**。

    见文件头"安全第一"：同系列固件对 lockStatus 写入是"假成功"，
    而 HA 的 lock 实体必然渲染上锁/解锁按钮。这里让按钮抛出自解释
    错误，而不是发出一条可能真实开锁（或被静默忽略）的指令。
    """

    async def refuse(context: DeviceContext, data: Mapping[str, Any]) -> None:
        del context, data
        raise ValueError(f"该门锁不支持远程{verb}，请直接使用门锁面板或官方 App 操作")

    return refuse


# ---------------------------------------------------------------------
# 状态读取
# ---------------------------------------------------------------------
def _status_reader() -> Callable[[DeviceContext], Any]:
    """保留最后一个"已声明"的 lockStatus 值。

    固件可能上报 Profile 未声明的过渡值（同系列观察到 7）。返回上一个
    已声明值可让 门锁 / 门 / 门锁状态 三个实体描述同一状态，
    而不是被过渡值一起清空。
    """

    cache: dict[str, Any] = {"status": None}

    def read(device: DeviceContext) -> Any:
        status = _int(device.value(_LOCK_STATUS_SID, _LOCK_STATUS_FIELD))
        if status in _DECLARED_STATUSES:
            cache["status"] = status
        return cache["status"]

    return read


# ---------------------------------------------------------------------
# 实体构造
# ---------------------------------------------------------------------
def _make_enum_switch(
    context: DeviceContext,
    sid: str,
    field_name: str,
    key: str,
    name: str,
) -> EntitySpec | None:
    """0/1 枚举开关（本机设置项几乎都是 enum 而非 bool）。"""

    field = _field(context.profile, sid, field_name)
    if field is None or not _is_writable(field):
        return None
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
        state=lambda device: {
            "is_on": _int(device.value(sid, field_name)) == 1
            if device.value(sid, field_name) is not None
            else None
        },
        actions={"turn_on": turn_on, "turn_off": turn_off},
    )


def _make_select(
    context: DeviceContext,
    sid: str,
    field_name: str,
    key: str,
    name: str,
    order: tuple[str, ...] | None,
) -> EntitySpec | None:
    field = _field(context.profile, sid, field_name)
    if field is None or not _is_writable(field):
        return None
    options = _enum_options(field, order)
    if not options:
        return None
    labels = tuple(label for _, label in options)
    by_label = {label: raw for raw, label in options}
    by_raw = {str(raw): label for raw, label in options}

    def state(device: DeviceContext) -> Mapping[str, Any]:
        raw = device.value(sid, field_name)
        if raw is None:
            return {"current_option": None}
        return {"current_option": by_raw.get(str(_int(raw)))}

    async def select(device: DeviceContext, data: Mapping[str, Any]) -> None:
        wanted = str(data.get("option"))
        raw = by_label.get(wanted)
        if raw is None:
            raise ValueError(f"unsupported option for {sid}.{field_name}: {wanted}")
        await device.async_send_service(sid, {field_name: _coerce(raw, field)})

    return EntitySpec(
        platform="select",
        key=key,
        name=name,
        state=state,
        metadata={"options": labels},
        actions={"select_option": select},
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


def _battery_spec(sid: str, key: str, name: str) -> EntitySpec:
    def state(device: DeviceContext) -> Mapping[str, Any]:
        value = _number(device.value(sid, _BATTERY_LEVEL_FIELD))
        # -1 是 Profile 的占位值，不是真实百分比。
        if value is not None and value <= _BATTERY_UNKNOWN:
            value = None
        return {"native_value": value}

    return EntitySpec(
        platform="sensor",
        key=key,
        name=name,
        state=state,
        metadata={
            "device_class": "battery",
            "state_class": "measurement",
            "unit": "%",
        },
    )


def _lock_alarm_is_stale(device: DeviceContext) -> bool:
    when = device.service_updated_at(_LOCK_ALARM_SID)
    if when is None:
        return False
    return datetime.now(timezone.utc) - when > _ALARM_PULSE_WINDOW


def _event_alarm_code(device: DeviceContext) -> int | None:
    code = _int(device.value(_EVENT_SID, _EVENT_DOOR_ALARM_FIELD))
    if code is None or code < 1:
        return None
    return code


# ---------------------------------------------------------------------
# 事件解码
# ---------------------------------------------------------------------
def _operation_direction(operation: Any) -> str | None:
    number = _int(operation)
    if number is None:
        return None
    if number in _INDOOR_UNLOCK_OPERATIONS:
        return "indoor"
    if number in _UNLOCK_OPERATIONS:
        return "outdoor"
    return None


def _event_kind(record: Mapping[str, Any]) -> str | None:
    """把一个事件记录分类为 unlock / lock / alarm。

    分类顺序与本适配器自身状态实体保持一致，避免事件与传感器
    对"发生了什么"给出矛盾说法。
    """

    alarm = _int(record.get(_EVENT_DOOR_ALARM_FIELD))
    if alarm is not None and alarm >= 1:
        return "alarm"
    operation = _int(record.get(_EVENT_OPERATION_FIELD))
    if operation == 25:  # 反锁
        return "lock"
    if _operation_direction(operation) is not None:
        return "unlock"
    # 未描述的操作码 + 有用户名，视为凭据开锁记录。
    user = _text(record.get(_EVENT_USER_NAME_FIELD))
    if user is not None and (
        _int(record.get(_EVENT_TYPE_FIELD)) == _EVENT_RECORD
    ):
        return "unlock"
    return None


def _lock_event_decoder(
    device: DeviceContext,
    sid: str,
    data: Mapping[str, Any],
    timestamp: str | None,
) -> list[tuple[str, Mapping[str, Any]]]:
    """把一次 event 推送转成 HA 事件。

    门锁对每次操作只推一次、从不推"已清除"，因此状态实体只能描述
    "最近发生过什么"。本解码器补上另一半：每次被接受的推送都触发一次
    事件，自动化应基于它，并可读 alarm_id 区分不同事件。
    """

    if sid != _EVENT_SID:
        return []

    kind = _event_kind(data)
    if kind is None:
        # 凭据管理、布防、门铃等记录不产生事件。
        return []

    operation = _int(data.get(_EVENT_OPERATION_FIELD))
    operation_field = _field(
        device.profile or {}, _EVENT_SID, _EVENT_OPERATION_FIELD
    )
    alarm_field = _field(
        device.profile or {}, _EVENT_SID, _EVENT_DOOR_ALARM_FIELD
    )

    payload: dict[str, Any] = {
        "alarm_id": _text(data.get(_EVENT_ALARM_ID_FIELD)),
        "user": _text(data.get(_EVENT_USER_NAME_FIELD)),
        "occurred_at": _text(data.get(_EVENT_TIME_FIELD)) or timestamp,
        "method": _enum_label(operation_field, operation),
        "direction": _operation_direction(operation),
    }
    alarm_code = _int(data.get(_EVENT_DOOR_ALARM_FIELD))
    if kind == "alarm":
        payload["alarm"] = _enum_label(alarm_field, alarm_code)
    return [(kind, {k: v for k, v in payload.items() if v is not None})]


class ProductKW5NAdapter:
    """Keep all KW5N entity and command choices in this file."""

    prod_id = "KW5N"

    def entities(self, context: DeviceContext) -> tuple[EntitySpec, ...]:
        profile = context.profile
        if profile is None:
            return ()

        entities: list[EntitySpec] = []
        read_status = _status_reader()

        # --- lock（只读；动作显式拒绝） -------------------------------
        if context.has_service(_LOCK_STATUS_SID):

            def lock_state(device: DeviceContext) -> Mapping[str, Any]:
                status = read_status(device)
                if status in _LOCKED_STATUSES:
                    return {"is_locked": True}
                if status in _UNLOCKED_STATUSES:
                    return {"is_locked": False}
                return {"is_locked": None}

            entities.append(
                EntitySpec(
                    platform="lock",
                    key="lock",
                    name="门锁",
                    state=lock_state,
                    actions={
                        "lock": _refusal_action("上锁"),
                        "unlock": _refusal_action("开锁"),
                    },
                )
            )

            # 门扇（只在语义明确的状态下判定）
            def door_state(device: DeviceContext) -> Mapping[str, Any]:
                status = read_status(device)
                if status in _DOOR_OPEN_STATUSES:
                    return {"is_on": True}
                if status in _DOOR_CLOSED_STATUSES:
                    return {"is_on": False}
                return {"is_on": None}

            entities.append(
                EntitySpec(
                    platform="binary_sensor",
                    key="door",
                    name="门",
                    state=door_state,
                    metadata={"device_class": "door"},
                )
            )

            # 门锁状态文字
            status_field = (
                _field(profile, _LOCK_STATUS_SID, _LOCK_STATUS_FIELD) or {}
            )

            def lock_status_state(device: DeviceContext) -> Mapping[str, Any]:
                value = read_status(device)
                if value is None:
                    return {"native_value": None}
                return {"native_value": _enum_label(status_field, value) or str(value)}

            entities.append(
                EntitySpec(
                    platform="sensor",
                    key="lock_status",
                    name="门锁状态",
                    state=lock_status_state,
                )
            )

        # --- 网络连通 -------------------------------------------------
        if context.has_service(_NET_STATE_SID):
            state_field = _field(profile, _NET_STATE_SID, _NET_STATE_FIELD)

            def connectivity_state(device: DeviceContext) -> Mapping[str, Any]:
                raw = _int(device.value(_NET_STATE_SID, _NET_STATE_FIELD))
                if raw is None:
                    return {"is_on": None}
                return {"is_on": raw == _NET_STATE_ONLINE}

            entities.append(
                EntitySpec(
                    platform="binary_sensor",
                    key="connectivity",
                    name="连接状态",
                    state=connectivity_state,
                    metadata={"device_class": "connectivity"},
                )
            )

            def net_state_text(device: DeviceContext) -> Mapping[str, Any]:
                raw = _int(device.value(_NET_STATE_SID, _NET_STATE_FIELD))
                if raw is None:
                    return {"native_value": None}
                return {
                    "native_value": _enum_label(state_field, raw) or str(raw)
                }

            entities.append(
                EntitySpec(
                    platform="sensor",
                    key="network_state",
                    name="网络状态",
                    state=net_state_text,
                    metadata={"entity_category": "diagnostic"},
                )
            )

        # --- 电池 -----------------------------------------------------
        if context.has_service(_DOOR_BATTERY_SID):
            entities.append(
                _battery_spec(_DOOR_BATTERY_SID, "door_battery", "门锁电量")
            )
        if context.has_service(_CAT_EYE_BATTERY_SID):
            entities.append(
                _battery_spec(_CAT_EYE_BATTERY_SID, "cat_eye_battery", "猫眼电量")
            )

        # --- 告警 -----------------------------------------------------
        if context.has_service(_LOCK_ALARM_SID):
            alarm_field = _field(profile, _LOCK_ALARM_SID, _LOCK_ALARM_FIELD)
            event_alarm_field = _field(
                profile, _EVENT_SID, _EVENT_DOOR_ALARM_FIELD
            )

            def alarm_state(device: DeviceContext) -> Mapping[str, Any]:
                value = _int(device.value(_LOCK_ALARM_SID, _LOCK_ALARM_FIELD))
                if (
                    value is not None
                    and value >= 1
                    and not _lock_alarm_is_stale(device)
                ):
                    return {
                        "native_value": _enum_label(alarm_field, value) or str(value)
                    }
                code = _event_alarm_code(device)
                if code is not None:
                    return {
                        "native_value": (
                            _enum_label(event_alarm_field, code) or str(code)
                        )
                    }
                if value is None and code is None:
                    return {"native_value": None}
                return {"native_value": _NO_ALARM}

            entities.append(
                EntitySpec(
                    platform="sensor",
                    key="alarm",
                    name="门锁告警",
                    state=alarm_state,
                )
            )

            def low_battery_state(device: DeviceContext) -> Mapping[str, Any]:
                value = _int(device.value(_LOCK_ALARM_SID, _LOCK_ALARM_FIELD))
                if (
                    value is not None
                    and value >= 1
                    and not _lock_alarm_is_stale(device)
                ):
                    return {"is_on": value == _ALARM_LOW_BATTERY}
                # 回退到事件里的低电告警码（doorAlarmState=4）。
                return {"is_on": _event_alarm_code(device) == 4}

            entities.append(
                EntitySpec(
                    platform="binary_sensor",
                    key="low_battery",
                    name="低电量告警",
                    state=low_battery_state,
                    metadata={"device_class": "battery"},
                )
            )

        # --- 事件实体 -------------------------------------------------
        if context.has_service(_EVENT_SID):
            entities.append(
                EntitySpec(
                    platform="event",
                    key="lock_event",
                    name="门锁事件",
                    state=lambda device: {},
                    metadata={
                        "event_types": ["unlock", "lock", "alarm"],
                        "icon": "mdi:door-open",
                    },
                    event_decoder=_lock_event_decoder,
                )
            )

        # --- 设置开关 -------------------------------------------------
        for sid, field_name, key, name in _SECURITY_SWITCHES:
            if not context.has_service(sid):
                continue
            spec = _make_enum_switch(context, sid, field_name, key, name)
            if spec is not None:
                entities.append(spec)

        for field_name, key, name in _ALARM_EVENT_SWITCHES:
            if not context.has_service("alarmEventSetting"):
                continue
            spec = _make_enum_switch(
                context, "alarmEventSetting", field_name, key, name
            )
            if spec is not None:
                entities.append(spec)

        for field_name, key, name in _CAT_EYE_SWITCHES:
            if not context.has_service("catEyeSetting"):
                continue
            spec = _make_enum_switch(
                context, "catEyeSetting", field_name, key, name
            )
            if spec is not None:
                entities.append(spec)

        if context.has_service("volumeSetting"):
            spec = _make_enum_switch(
                context, "volumeSetting", "nightModeSwitch", "night_mode", "夜间模式"
            )
            if spec is not None:
                entities.append(spec)

        # --- 设置下拉 -------------------------------------------------
        for sid, field_name, key, name, order in _SELECT_SPECS:
            if not context.has_service(sid):
                continue
            spec = _make_select(context, sid, field_name, key, name, order)
            if spec is not None:
                entities.append(spec)

        # --- 诊断实体（默认关闭，见文件头说明） ----------------------
        if _ENABLE_DIAGNOSTIC_ENTITIES:
            entities.extend(_make_diagnostic_entities(context))

        return tuple(entities)



def _make_diagnostic_entities(
    context: DeviceContext,
) -> tuple[EntitySpec, ...]:
    """Build the netInfo / update diagnostic entities.

    默认不创建（见 ``_ENABLE_DIAGNOSTIC_ENTITIES``）。代码保留是为了：
    若日后在真机上确认这些字段**确实会上报**，把开关打开即可恢复，
    无需重新实现。取值逻辑未做任何猜测，仍是按 Profile 的字段读取。
    """

    out: list[EntitySpec] = []

    # --- 网络诊断 -------------------------------------------------
    if context.has_service("netInfo"):
        # 本机 intensity 是 0~100 连续整数（非同系列的 20/40/60/80/100
        # 五档编码），故按原始数值输出，不做格数换算。
        out.append(
            _make_sensor(
                "netInfo", "intensity", "wifi_signal_level",
                "Wi-Fi 信号强度",
                state_class="measurement", entity_category="diagnostic",
                decode=_int,
            )
        )
        out.append(
            _make_sensor(
                "netInfo", "RSSI", "wifi_rssi", "Wi-Fi RSSI",
                unit="dBm", device_class="signal_strength",
                state_class="measurement", entity_category="diagnostic",
                decode=_int,
            )
        )
        out.append(
            _make_sensor(
                "netInfo", "IP", "ip_address", "IP 地址",
                entity_category="diagnostic", decode=_text,
            )
        )
        out.append(
            _make_sensor(
                "netInfo", "SSID", "wifi_ssid", "Wi-Fi SSID",
                entity_category="diagnostic", decode=_text,
            )
        )
        out.append(
            _make_sensor(
                "netInfo", "BSSID", "bssid", "路由器 BSSID",
                entity_category="diagnostic", decode=_text,
            )
        )

    # --- 固件版本（诊断） -----------------------------------------
    if context.has_service("update"):
        out.append(
            _make_sensor(
                "update", "version", "firmware_version", "固件版本",
                entity_category="diagnostic", decode=_text,
            )
        )

    return tuple(out)

ADAPTER = ProductKW5NAdapter()
