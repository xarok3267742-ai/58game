# Deobfuscation Notes

Date: June 14, 2026.

Release builds enable R8 minification and resource shrinking. Keep the release mapping outputs with every uploaded AAB so crash reports can be decoded against the exact binary.

## Source
```text
app/build/outputs/mapping/release/
```

Expected files:
- `mapping.txt`
- `configuration.txt`
- `resources.txt`
- `seeds.txt`
- `usage.txt`

## Handoff Copy
`python3 scripts/create_play_handoff.py` copies these files to:

```text
build/play_handoff/shawarma58-v1.0.0/deobfuscation/release/
```

`python3 scripts/play_handoff_qa.py` verifies that the copied files match the current Gradle outputs by SHA-256.

## Handling
Do not publish mapping files as store graphics or public documentation. Store them with the release record and upload/use them only in Play Console or crash-investigation tooling when needed.
