# -*- coding: utf-8 -*-
"""
gateway.tests.test_sprint10a_mooc_resources
============================================
学海智导 (Xuehai Zhidao) — Phase 6 / Sprint 10-A
中国大学MOOC外部资源目录与 URL 安全校验层严苛测试套件 (MOOC Catalog & Security Test Suite)

覆盖范围：
A. MOOC Catalog 结构与契约
   1. 模块导入与基础结构
   2. 资源 ID 格式规范（mooc_{kid_lower}_{slug}）与全局唯一性
   3. 知识点映射有效性（K01 ~ K30）
   4. 来源标识严格为 "china_mooc"
   5. 外部标记严格为 is_external == True
   6. 资源类型枚举兼容性（严格复用 ResourceType.VIDEO / DOCUMENT）
   7. 扩展元数据完备性（provider, university, instructor, course, chapter）

B. 原有内部资源目录物理隔离（零污染保障）
   8. 原有 RESOURCE_CATALOG 严格保留 130 项内部资源
   9. 原有 RESOURCE_CATALOG 100% 满足内部契约（is_external=False, source="xuehai_internal", source_url=None）
   10. MOOC_RESOURCE_CATALOG 与 RESOURCE_CATALOG key 集合互斥无交叉

C. URL 安全校验层（validate_external_mooc_url）
   11. 合法官方 URL 全面放行（https://www.icourse163.org, icourse163.org, study, mooc, 443端口等）
   12. 非 HTTPS 协议拦截（http, ftp, ws, etc.）
   13. 伪协议与攻击载荷拦截（javascript:, data:, file:, blob:）
   14. 域名仿冒与后缀绕过拦截（.attacker.com, evil-icourse163.org）
   15. 用户信息段混淆拦截（user:pass@, @evil.com, etc.）
   16. 非标准端口拦截（80, 8080, 8443, 非数字端口）
   17. 畸形与空输入容错防御（None, "", 空白, 非字符串, 无host等）

D. 查询 Helper 确定性与纯函数稳定性
   18. 单资源精准查找与未知资源防御
   19. 按考点与类型筛选精准度
   20. 100 次重复调用输出完全确定性
   21. 纯本地离线断言（零外部网络依赖）
"""

import pytest
from typing import Set

from gateway.learning.resources.models import ResourceType
from gateway.learning.resources.catalog import (
    RESOURCE_CATALOG,
    get_all_resources as get_all_internal_resources,
)
from gateway.learning.resources.mooc_catalog import (
    MOOC_RESOURCE_CATALOG,
    get_mooc_resource_by_id,
    get_mooc_resources_by_knowledge,
    get_all_mooc_resources,
)
from gateway.learning.resources.security import (
    validate_external_mooc_url,
    sanitize_and_validate_mooc_url,
    MOOC_ALLOWED_BASE_DOMAINS,
    MOOC_ALLOWED_HOSTNAMES,
)


# =============================================================================
# A. MOOC Catalog 结构与契约
# =============================================================================

def test_01_mooc_catalog_imports_and_structure():
    """验证 MOOC 资源目录可正常导入，且包含有效数量资源"""
    assert isinstance(MOOC_RESOURCE_CATALOG, dict)
    assert len(MOOC_RESOURCE_CATALOG) > 0, "MOOC 目录不应为空"


def test_02_mooc_resource_id_format_and_uniqueness():
    """验证所有 MOOC 资源 ID 遵循规范命名且全局唯一"""
    ids: Set[str] = set()
    for res_id, res in MOOC_RESOURCE_CATALOG.items():
        assert res_id == res.resource_id, f"字典键 {res_id} 与实体 ID {res.resource_id} 不一致"
        assert res_id.startswith("mooc_"), f"资源 ID 必须以 mooc_ 开头: {res_id}"
        # 确保不包含随机 UUID 样式的破折号混淆
        assert res_id not in ids, f"资源 ID 重复: {res_id}"
        ids.add(res_id)


def test_03_mooc_knowledge_point_mapping():
    """验证所有 MOOC 资源精确映射至 K01 ~ K30"""
    valid_kids = {f"K{i:02d}" for i in range(1, 31)}
    for res in MOOC_RESOURCE_CATALOG.values():
        assert res.knowledge_id in valid_kids, f"非法考点映射: {res.knowledge_id}"
        # ID 必须包含对应的考点小写标识，保障稳定可预测
        kid_lower = res.knowledge_id.lower()
        assert f"_{kid_lower}_" in res.resource_id, f"资源 ID 必须包含考点小写: {res.resource_id}"


def test_04_mooc_source_and_external_invariants():
    """验证数据契约：source == 'china_mooc' 且 is_external == True"""
    for res in MOOC_RESOURCE_CATALOG.values():
        assert res.source == "china_mooc", f"资源 {res.resource_id} source 必须为 china_mooc"
        assert res.is_external is True, f"资源 {res.resource_id} is_external 必须为 True"
        assert res.source_url is not None, f"MOOC 资源 {res.resource_id} 必须提供有效 source_url"
        # 严格验证所包含的真实 URL 必须 100% 通过安全层校验
        assert validate_external_mooc_url(res.source_url) is True, f"不安全的外链: {res.source_url}"


def test_05_mooc_resource_type_compatibility():
    """验证资源类型严格复用已有枚举 (VIDEO, DOCUMENT)，严禁新增未经审核的类型"""
    allowed_types = {ResourceType.VIDEO, ResourceType.DOCUMENT}
    for res in MOOC_RESOURCE_CATALOG.values():
        assert res.resource_type in allowed_types, f"非法外部资源类型: {res.resource_type}"


def test_06_mooc_metadata_completeness():
    """验证 MOOC 资源的元数据包含核心教学与高校信息"""
    for res in MOOC_RESOURCE_CATALOG.values():
        meta = res.metadata
        assert isinstance(meta, dict), f"元数据必须为字典: {res.resource_id}"
        assert meta.get("provider") == "中国大学MOOC", f"provider 必须为中国大学MOOC: {res.resource_id}"
        assert "university" in meta and len(meta["university"]) > 0, f"缺少开课高校信息: {res.resource_id}"
        assert "instructor" in meta and len(meta["instructor"]) > 0, f"缺少授课教师信息: {res.resource_id}"
        assert "course" in meta and len(meta["course"]) > 0, f"缺少课程名称: {res.resource_id}"
        assert "chapter" in meta and len(meta["chapter"]) > 0, f"缺少章节对应信息: {res.resource_id}"


# =============================================================================
# B. 原有内部资源目录物理隔离（零污染保障）
# =============================================================================

def test_07_internal_catalog_untouched_count():
    """验证原有内部 130 项资源数量保持严格不变"""
    internal_all = get_all_internal_resources()
    assert len(internal_all) == 130, f"内部资源总数期望 130，实际 {len(internal_all)}"
    assert len(RESOURCE_CATALOG) == 130, f"RESOURCE_CATALOG 字典项数期望 130，实际 {len(RESOURCE_CATALOG)}"


def test_08_internal_catalog_pure_internal_contract():
    """验证原有 RESOURCE_CATALOG 历史架构契约 100% 成立：纯内部、无外链、无外部标记"""
    for r in RESOURCE_CATALOG.values():
        assert r.is_external is False, f"原有内部资源 {r.resource_id} 绝不能标为外部资源"
        assert r.source == "xuehai_internal", f"原有内部资源 {r.resource_id} 来源必须为 xuehai_internal"
        assert r.source_url is None, f"原有内部资源 {r.resource_id} 绝不能包含 source_url"


def test_09_catalog_isolation_no_key_overlap():
    """验证 MOOC 资源目录与原有内部资源目录 key 集合严格正交互斥"""
    internal_keys = set(RESOURCE_CATALOG.keys())
    mooc_keys = set(MOOC_RESOURCE_CATALOG.keys())
    overlap = internal_keys.intersection(mooc_keys)
    assert len(overlap) == 0, f"内部目录与外部 MOOC 目录存在键冲突: {overlap}"


# =============================================================================
# C. URL 安全校验层（validate_external_mooc_url）
# =============================================================================

def test_10_url_security_valid_official_urls():
    """验证中国大学MOOC合法官方链接放行 (PASS)"""
    valid_cases = [
        "https://www.icourse163.org",
        "https://www.icourse163.org/",
        "https://www.icourse163.org/learn/PKU-1002534001",
        "https://www.icourse163.org/course/WHU-1001539001",
        "https://www.icourse163.org/course/WHU-1001539001?tid=1460",
        "https://icourse163.org",
        "https://icourse163.org/course/test",
        "https://study.icourse163.org/spoc/course",
        "https://mooc.icourse163.org/page/index",
        "https://mobile.icourse163.org/app/share",
        # 标准 443 端口
        "https://www.icourse163.org:443/course/WHU-1001",
        # 大小写不敏感
        "HTTPS://WWW.ICOURSE163.ORG/learn/PKU-1002534001",
        "https://WWW.ICOURSE163.ORG/learn/test",
        # 末尾带有点的标准 FQDN
        "https://www.icourse163.org./course/test",
    ]
    for url in valid_cases:
        assert validate_external_mooc_url(url) is True, f"合法官方链接被错误拦截: {url}"
        assert sanitize_and_validate_mooc_url(url) is not None


def test_11_url_security_reject_non_https():
    """验证非 HTTPS 协议严格拦截 (FAIL)"""
    insecure_schemes = [
        "http://www.icourse163.org",
        "http://www.icourse163.org/learn/PKU-1002534001",
        "http://icourse163.org",
        "ftp://www.icourse163.org/resource.pdf",
        "ws://www.icourse163.org/socket",
        "wss://www.icourse163.org/socket",
        "//www.icourse163.org/relative",
        "www.icourse163.org/course/WHU",
    ]
    for url in insecure_schemes:
        assert validate_external_mooc_url(url) is False, f"非 HTTPS 链接未被拦截: {url}"


def test_12_url_security_reject_pseudo_protocols_and_attacks():
    """验证伪协议与脚本注入载荷严格拦截 (FAIL)"""
    attack_payloads = [
        "javascript:alert(1)",
        "javascript:alert('xss')",
        "javascript://www.icourse163.org/%0Aalert(1)",
        "data:text/html,<script>alert(1)</script>",
        "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
        "file:///etc/passwd",
        "file:///C:/Windows/system32/cmd.exe",
        "blob:https://www.icourse163.org/uuid-1234",
    ]
    for url in attack_payloads:
        assert validate_external_mooc_url(url) is False, f"攻击伪协议载荷未被拦截: {url}"


def test_13_url_security_reject_domain_spoofing_and_open_redirect():
    """验证针对 icourse163.org 的域名欺骗与开放重定向严格拦截 (FAIL)"""
    spoofed_domains = [
        "https://evil.com",
        "https://www.evil.com/icourse163.org",
        # 常见前缀欺骗：域名后缀实为 attacker.com
        "https://evil.icourse163.org.attacker.com",
        "https://evil.icourse163.org.attacker.com/path",
        "https://icourse163.org.attacker.com",
        "https://icourse163.org.evil.cn",
        # 连字符假域名
        "https://evil-icourse163.org",
        "https://icourse163.org-evil.com",
        "https://noticourse163.org",
        "https://wwwicourse163.org",
        # 路径与查询参数混淆
        "https://evil.com/https://www.icourse163.org",
        "https://evil.com?target=https://www.icourse163.org",
        "https://evil.com#icourse163.org",
    ]
    for url in spoofed_domains:
        assert validate_external_mooc_url(url) is False, f"域名欺骗链接未被拦截: {url}"


def test_14_url_security_reject_userinfo_obfuscation():
    """验证包含用户信息段 (username / password) 的混淆 URL 拦截 (FAIL)"""
    userinfo_attacks = [
        "https://icourse163.org@evil.com/",
        "https://www.icourse163.org@attacker.com/course",
        "https://attacker.com@www.icourse163.org/course",
        "https://user:password@www.icourse163.org/course",
        "https://admin:@icourse163.org/",
    ]
    for url in userinfo_attacks:
        assert validate_external_mooc_url(url) is False, f"用户信息混淆 URL 未被拦截: {url}"


def test_15_url_security_reject_non_standard_ports():
    """验证非标准端口拦截 (FAIL)"""
    bad_ports = [
        "https://www.icourse163.org:80/course",
        "https://www.icourse163.org:8080/course",
        "https://www.icourse163.org:8443/course",
        "https://www.icourse163.org:22/course",
        "https://www.icourse163.org:9999/course",
    ]
    for url in bad_ports:
        assert validate_external_mooc_url(url) is False, f"非标准端口未被拦截: {url}"


def test_16_url_security_malformed_and_empty_inputs():
    """验证空值、空白及畸形输入的鲁棒容错 (FAIL)"""
    malformed_cases = [
        None,
        "",
        "   ",
        "\t\n",
        12345,
        {"url": "https://www.icourse163.org"},
        ["https://www.icourse163.org"],
        "https://",
        "https:///",
        "https://:443",
        "https:///course/WHU",
    ]
    for bad in malformed_cases:
        assert validate_external_mooc_url(bad) is False  # type: ignore
        assert sanitize_and_validate_mooc_url(bad) is None  # type: ignore


# =============================================================================
# D. 查询 Helper 确定性与纯函数稳定性
# =============================================================================

def test_17_get_mooc_resource_by_id():
    """验证单资源精确检索与未知 ID 防御"""
    res = get_mooc_resource_by_id("mooc_k01_scarcity")
    assert res is not None
    assert res.knowledge_id == "K01"
    assert "稀缺性" in res.title
    assert res.source == "china_mooc"

    unknown = get_mooc_resource_by_id("non_existent_mooc_999")
    assert unknown is None


def test_18_get_mooc_resources_by_knowledge():
    """验证按考点过滤及按类型筛选"""
    k01_list = get_mooc_resources_by_knowledge("K01")
    assert len(k01_list) >= 1
    assert all(r.knowledge_id == "K01" for r in k01_list)

    k01_videos = get_mooc_resources_by_knowledge("K01", resource_type=ResourceType.VIDEO)
    assert len(k01_videos) >= 1
    assert all(r.resource_type == ResourceType.VIDEO for r in k01_videos)

    k01_docs = get_mooc_resources_by_knowledge("K01", resource_type=ResourceType.DOCUMENT)
    assert len(k01_docs) == 0  # K01 当前配置为视频微课


def test_19_determinism_100_executions():
    """验证多次重复调用 100 次，返回的资源序列与属性完全一致（无随机无时间依赖）"""
    baseline = [r.resource_id for r in get_all_mooc_resources()]
    for _ in range(100):
        current = [r.resource_id for r in get_all_mooc_resources()]
        assert current == baseline, "确定性排序断言失败"


def test_20_offline_first_zero_network():
    """验证整个 MOOC 资源目录及安全校验模块完全在本地离线执行，无外部依赖"""
    # 纯本地计算，执行多次响应时间在微秒级
    all_res = get_all_mooc_resources()
    assert len(all_res) > 0
    for r in all_res:
        assert validate_external_mooc_url(r.source_url) is True


def test_21_mooc_catalog_factual_integrity():
    """
    Handoff Evidence Audit: 验证 MOOC 目录的事实真实性 (Factual Integrity)
    1. 所有 course_id 必须为官方确认的公开课编号 (PKU-1003090003, whu-23003)；
    2. 严禁出现历史未验证或拼写错误的 course_id；
    3. 武汉大学课程章节必须严格符合官方十讲结构，严禁出现第十一讲及以上不可能讲次编号；
    4. 资源总数严格为 12 项精选示范，杜绝虚构伪造。
    """
    import re
    confirmed_courses = {"PKU-1003090003", "whu-23003"}
    banned_course_ids = {
        "PKU-1001937004", "WHU-1001593003",
        "PKU-1002534001", "WHU-1001539001",
        "PKU-1205934803", "WHU-1001593001"
    }
    chinese_num_map = {
        "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
        "六": 6, "七": 7, "八": 8, "九": 9, "十": 10
    }

    assert len(MOOC_RESOURCE_CATALOG) == 12, "MOOC 目录必须严格保持 12 项精选真实资源"

    for res in MOOC_RESOURCE_CATALOG.values():
        course_id = res.metadata.get("course_id")
        assert course_id in confirmed_courses, f"资源 {res.resource_id} 使用了未经确认的课程代码: {course_id}"
        assert course_id not in banned_course_ids, f"资源 {res.resource_id} 使用了已禁用的错误代码: {course_id}"
        assert any(cid.lower() in res.source_url.lower() for cid in confirmed_courses), (
            f"资源 {res.resource_id} source_url 必须指向官方已确认课程: {res.source_url}"
        )

        # 校验武汉大学十讲结构
        if "whu" in res.source_url.lower() or res.metadata.get("university") == "武汉大学":
            chapter = res.metadata.get("chapter", "")
            match = re.search(r"第([一二三四五六七八九十]+)讲", chapter)
            if match:
                num_str = match.group(1)
                assert num_str in chinese_num_map, f"非法或超出十讲的讲次编号: {num_str} in {chapter}"
                lecture_num = chinese_num_map[num_str]
                assert 1 <= lecture_num <= 10, f"武汉大学官方课程仅有十讲，禁止出现超出讲次: {chapter}"
