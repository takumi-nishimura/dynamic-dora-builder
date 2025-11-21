# Dynamic Dataflow Builder

DORAのDataflow YAMLを動的に組み立てる軽量ビルダー．デプロイメント用YAMLからノード・オペレーター・テンプレートコンポーネントを統合し，パス解決やテンプレート展開を自動で実施する．CLIとPython APIの両方から利用可能．

## 特徴
- 単一のデプロイメントYAMLから最終的なDataflow YAMLを生成
- `kind: dynamic`ノードで既存データフローから任意のノードを取り込み再利用
- コンポーネントをJinja2テンプレートとして展開し，環境変数などで構成を切り替え
- パスはデプロイメントYAML or カレントディレクトリ基準で解決し，出力はカレントディレクトリ相対に正規化
- CLIは標準出力へも出力可能で，書き出し先が明示されない場合は`dataflow.yml`に保存

## セットアップ
- 前提: Python 3.12+，`uv`
- 依存関係: `uv sync`
- 以降のコマンドはリポジトリ直下で`uv run ...`として実行

## 使い方 (CLI)
デプロイメントYAMLから最終データフローを生成してファイルと標準出力に出す例:

```bash
uv run dynamic-dora-builder build path/to/deployment.yml --export out/dataflow.yml --stdout
```

- `--export`未指定時はカレントディレクトリ直下の`dataflow.yml`へ書き出し，標準出力にも表示
- `deployment`の存在チェックと`--export`のディレクトリ指定はCLI側でバリデート済み

## デプロイメントYAMLの書き方
トップレベルキー: `nodes`と`components` (どちらも任意)．

### nodesセクション
3種類を混在可能:

- Node: 明示的なノード定義
  ```yaml
  nodes:
    - id: webcam
      path: apps/webcam_node
      env:
        FPS: 30
      operator:
        python: ops/webcam.py
        inputs:
          tick: dora/timer/millis/100
        outputs:
          - image
  ```
- Operator: オペレーターだけを直接並べたい場合に利用 (暗黙のidなしで配置)
  ```yaml
  nodes:
    - python: ops/cleanup.py
      inputs:
        image: webcam/image
  ```
- DynamicNode (`kind: dynamic`): 既存データフローYAMLから特定idのノードを取り込む
  ```yaml
  nodes:
    - id: plot
      path: samples/dataflow/plot.yml
      kind: dynamic
  ```
  `path`で指定したデータフローYAMLを読み込み，同じ`id`のノードを抽出して接続．

### componentsセクション
Jinja2テンプレートを用いた動的生成．`env`をテンプレートに渡す:

```yaml
components:
  - id: camera_chain
    path: templates/camera_chain.yml.j2
    env:
      source_topic: webcam/image
      every_ms: 100
```

テンプレート例 (`templates/camera_chain.yml.j2`):
```yaml
nodes:
  - id: gate
    operator:
      python: ops/gate.py
      inputs:
        image: {{ source_topic }}
        tick: dora/timer/millis/{{ every_ms }}
      outputs:
        - gated_image
```
テンプレートは`deployment`のディレクトリ基準で解決 (なければカレントディレクトリ)．`env`はネストした値もそのまま埋め込める．

### デプロイメントYAMLをJinja2で書く
`deployment.yml`自体もJinja2として描画される．利用できるコンテキスト:
- `env`: OS環境変数 (`{{ env.PATH }}` や `{{ env["GPU_ID"] }}`)
- `cwd`: コマンド実行時のカレントディレクトリ文字列

例 (ループと環境変数):
```yaml
{% set inputs = [
  {"id": "cam1", "topic": "cam1/image"},
  {"id": "cam2", "topic": "cam2/image"},
] %}
nodes:
{% for s in inputs %}
  - id: {{ s.id }}
    operator:
      python: ops/pipe.py
      inputs:
        image: {{ s.topic }}
        device: {{ env.get("GPU_ID", "0") }}
{% endfor %}
```
未定義変数はStrictUndefinedでエラーになるため，環境変数を使う場合は存在を確認するか`get`でデフォルトを入れる．拡張子は`.yml`でも`.yml.j2`でも可．

### パス解決と出力
- 相対パスは「デプロイメントYAMLの場所」優先で解決し，存在しない場合はカレントディレクトリを探索
- 出力されるDataflow YAML内のパスはカレントディレクトリ基準の相対パスに正規化
- 出力時に`--stdout`指定がなくても，`--export`を省略すると標準出力にも表示される

## サンプル
リポジトリ同梱のWebカメラ→プロット構成:

```bash
uv run dynamic-dora-builder build samples/dataflow/webcam_plot.yml --export out/webcam_plot.yml
```

`samples/dataflow/webcam_plot.yml`では`kind: dynamic`で`webcam.yml`と`plot.yml`からノードを取り込み，最終的な`out/webcam_plot.yml`に統合される．

## Python APIで使う
```python
from pathlib import Path
from dynamic_dora_builder import DynamicDataflowBuilder

dataflow = DynamicDataflowBuilder.build(
    deployment_path=Path("deployment.yml"),
    export_path=Path("out/dataflow.yml"),
)
print(dataflow.model_dump())  # pydanticモデルとして利用可能
```

## よく使うコマンド
- ビルド: `uv run dynamic-dora-builder build deployment.yml --export out/dataflow.yml`
- 標準出力だけ欲しい場合: `uv run dynamic-dora-builder build deployment.yml --stdout --export /tmp/ignore.yml`
