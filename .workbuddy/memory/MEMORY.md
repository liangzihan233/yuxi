# 项目长期记忆

## 火山引擎 RTC-AIGC 配置

### 环境变量
| 变量名 | 值 | 来源 |
|---|---|---|
| VOLC_ACCESS_KEY_ID | <见.env文件> | Custom.json AccountConfig |
| VOLC_SECRET_KEY | <见.env文件> | Custom.json SecretKey base64解码 |
| RTC_APP_ID | <见.env文件> | Custom.json RTCConfig |
| ARK_ENDPOINT_ID | <见.env文件> | Custom.json LLMConfig |
| VOLC_ASR_APP_ID | <见.env文件> | Custom.json ASRConfig |
| VOLC_TTS_APP_ID | <见.env文件> | Custom.json TTSConfig |
| RTC_APP_KEY | <见.env文件> | 火山引擎 RTC 控制台 |

### ASR/TTS 配置
- ASR Mode: `smallmodel`
- ASR Cluster: `volcengine_streaming_common`
- TTS Cluster: `volcano_tts`
- Voice Type: `BV001_streaming`
- LLM Mode: `ArkV3`
- InterruptMode: `0`

### 配置状态
- 所有环境变量已配置完成，后端容器已重启加载
