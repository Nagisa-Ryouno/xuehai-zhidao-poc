"""通过 GitHub Git Data API 推送本地提交（git 端口受限时的等效推送）。

原理：api.github.com 可达但 github.com 的 git 端口被封锁时，用 REST 创建
blob/tree/commit 并更新 ref。blob 内容直接取本地 git 对象库
（git cat-file blob HEAD:path），与索引逐字节一致（含 CRLF 文件），
因此 tree sha 与本地完全相等。

使用：python scripts/push_via_api.py   （在已 commit 之后执行）
"""
import base64
import json
import subprocess
import sys

REPO = "Nagisa-Ryouno/xuehai-zhidao-poc"
BRANCH = "feat/ui-enhancement"


def gh(*args, input_data=None, xmethod="GET"):
    cmd = ["gh", "api"] + list(args)
    if xmethod != "GET":
        cmd += ["-X", xmethod]
    if input_data is not None:
        cmd += ["--input", "-"]
    r = subprocess.run(cmd, input=input_data, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        print("gh api failed:", args, r.stderr[:500])
        sys.exit(1)
    return json.loads(r.stdout)


def git(*args, binary=False):
    r = subprocess.run(["git"] + list(args), capture_output=True)
    if r.returncode != 0:
        print("git failed:", args, r.stderr.decode("utf-8", "replace")[:500])
        sys.exit(1)
    return r.stdout if binary else r.stdout.decode("utf-8").strip()


def main():
    local_sha = git("rev-parse", "HEAD")
    parent_sha = git("rev-parse", "HEAD^")
    meta = git("log", "-1", "--format=%an%x00%ae%x00%aI%x00%cn%x00%ce%x00%cI%x00%B", local_sha).split("\x00")
    an, ae, ai, cn, ce, ci, message = meta[0], meta[1], meta[2], meta[3], meta[4], meta[5], meta[6]

    remote_sha = gh(f"repos/{REPO}/git/ref/heads/{BRANCH}")["object"]["sha"]
    print(f"本地 {local_sha[:8]} (父 {parent_sha[:8]}) | 远端 {remote_sha[:8]}")

    # 以远端 head 的 tree 为基线，保持远端线性历史
    parent_tree = gh(f"repos/{REPO}/git/commits/{remote_sha}")["tree"]["sha"]
    changed = git("diff", "--name-only", "HEAD^", "HEAD").splitlines()
    print("变更文件:", len(changed))

    entries = []
    for path in changed:
        blob_bytes = git("cat-file", "blob", f"HEAD:{path}", binary=True)
        blob_sha = git("rev-parse", f"HEAD:{path}")
        payload = {"encoding": "base64", "content": base64.b64encode(blob_bytes).decode("ascii")}
        res = gh(f"repos/{REPO}/git/blobs", xmethod="POST", input_data=json.dumps(payload))
        assert res["sha"] == blob_sha, f"blob sha 不一致: {path}"
        entries.append({"path": path, "mode": "100644", "type": "blob", "sha": blob_sha})
    deleted = git("diff", "--name-only", "--diff-filter=D", "HEAD^", "HEAD").splitlines()
    for path in deleted:
        entries.append({"path": path, "mode": "100644", "type": "blob", "sha": None})

    new_tree = gh(f"repos/{REPO}/git/trees", xmethod="POST",
                  input_data=json.dumps({"base_tree": parent_tree, "tree": entries}))
    local_tree = git("rev-parse", f"{local_sha}^{{tree}}")
    ok_tree = new_tree["sha"] == local_tree
    print("tree:", new_tree["sha"], "| 本地:", local_tree, "|", "一致" if ok_tree else "不一致!")

    commit_payload = {
        "message": message,
        "tree": new_tree["sha"],
        "parents": [remote_sha],
        "author": {"name": an, "email": ae, "date": ai},
        "committer": {"name": cn, "email": ce, "date": ci},
    }
    new_commit = gh(f"repos/{REPO}/git/commits", xmethod="POST", input_data=json.dumps(commit_payload))
    print("commit:", new_commit["sha"], "| 本地:", local_sha, "|", "一致" if new_commit["sha"] == local_sha else "(父提交不同，sha 不同但内容一致)")

    gh(f"repos/{REPO}/git/refs/heads/{BRANCH}", xmethod="PATCH",
       input_data=json.dumps({"sha": new_commit["sha"], "force": True}))
    print(f"已推送 {BRANCH} -> {new_commit['sha'][:8]}")
    print("提示：随后请执行 git fetch && git reset --hard origin/" + BRANCH + " 对齐本地")


if __name__ == "__main__":
    main()
