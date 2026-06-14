package handlers

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"golang.org/x/crypto/bcrypt"
	"gorm.io/gorm"

	"my-shop/models"
)

type SetupHandler struct {
	DB *gorm.DB
}

func (h *SetupHandler) Status(c *gin.Context) {
	var count int64
	h.DB.Model(&models.User{}).Where("is_admin = ?", true).Count(&count)
	c.JSON(http.StatusOK, gin.H{"setup_required": count == 0})
}

func (h *SetupHandler) Init(c *gin.Context) {
	var count int64
	h.DB.Model(&models.User{}).Where("is_admin = ?", true).Count(&count)
	if count > 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "管理员已存在，不能重复初始化"})
		return
	}

	var req struct {
		Username string `json:"username" binding:"required,min=3,max=50"`
		Password string `json:"password" binding:"required,min=6,max=100"`
		Email    string `json:"email"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	hash, _ := bcrypt.GenerateFromPassword([]byte(req.Password), 4)
	user := models.User{
		Username: req.Username,
		Password: string(hash),
		Email:    req.Email,
		IsAdmin:  true,
		Level:    models.LevelDiamond,
	}
	if err := h.DB.Create(&user).Error; err != nil {
		c.JSON(http.StatusConflict, gin.H{"error": "用户名已存在"})
		return
	}
	c.JSON(http.StatusCreated, gin.H{"message": "管理员创建成功", "user_id": user.ID})
}
