# \[!\[Google Drive](https://img.shields.io/badge/Video%20Demo-34A853?style=for-the-badge\&logo=googledrive\&logoColor=white)](https://drive.google.com/file/d/1RWLBkc82JlwF0ULHlVz6jSsTjlWlXnMt/view?usp=drive\_link)

# \[!\[Git Game](https://img.shields.io/badge/Link%20GitGame-181717?style=for-the-badge\&logo=github\&logoColor=white)](https://github.com/vuquocdung04/Dreamy-Room)

# 

# !\[Pic1](0\_Pic1.png)

# !\[Pic2](0\_Pic2.png)

# !\[Pic3](0\_Pic3.png)

# 

# 

# \# Hand Tracking Controller — Python to Unity

# 

# 

# Điều khiển game Unity bằng tay không qua webcam, sử dụng MediaPipe để nhận diện tay và truyền dữ liệu sang Unity qua UDP theo thời gian thực.

# 

# \---

# 

# \## Luồng kết nối Python to Unity

# 

# \### Python gửi (UDP Client)

# 

# Python gửi một chuỗi ASCII mỗi frame theo định dạng `"x,y,pinch"`, trong đó X và Y là tọa độ chuẩn hóa trong khoảng `\[0.0 → 1.0]` của đầu ngón trỏ, và pinch là trạng thái nhón tay (0 hoặc 1).

# 

# \### Unity nhận (UDP Server)

# 

# `UDPReceiver.cs` lắng nghe trên một luồng riêng để không block main thread. Mỗi packet được parse và lưu vào biến, sau đó `Update()` đọc và đẩy vào `InputManager`.

# 

# \### Unity xử lý input

# 

# `InputManager.cs` dùng `Vector3.Lerp` để làm mượt vị trí cursor, sau đó dùng `Physics2D.OverlapCircle` để hit-test với các object trong game.

# 

# \---

# 

# \## Thuật toán python chính

# 

# \- \*\*MediaPipe Hand Landmark Detection\*\* — Trả về 21 keypoint trên bàn tay.

# \- \*\*Scale-Invariant Pinch Detection\*\* — Giải quyết vấn đề tay tiến/lùi khiến độ nhạy thay đổi.

# \- \*\*Hysteresis State Machine\*\* — Xử lí điều kiện kéo thả vật.

# \- \*\*One Euro Filter\*\* — Tự động điều chỉnh cutoff frequency theo vận tốc tức thời: đứng yên thì lọc mạnh khử jitter, di chuyển nhanh thì lọc nhẹ để bám sát và giảm độ trễ.

# 

# 

# \---

