package handlers

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"

	"my-shop/models"
)

type CategoryHandler struct {
	DB *gorm.DB
}

func (h *CategoryHandler) List(c *gin.Context) {
	var cats []models.ProductCategory
	h.DB.Order("sort_order asc").Find(&cats)
	c.JSON(http.StatusOK, cats)
}

func (h *CategoryHandler) Create(c *gin.Context) {
	var req struct {
		Name        string `json:"name" binding:"required"`
		Description string `json:"description"`
		SortOrder   int    `json:"sort_order"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	cat := models.ProductCategory{Name: req.Name, Description: req.Description, SortOrder: req.SortOrder}
	h.DB.Create(&cat)
	c.JSON(http.StatusCreated, cat)
}

func (h *CategoryHandler) Update(c *gin.Context) {
	id, _ := parseInt(c.Param("id"), 0)
	var cat models.ProductCategory
	if err := h.DB.First(&cat, id).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "分类不存在"})
		return
	}
	var req struct {
		Name        string `json:"name" binding:"required"`
		Description string `json:"description"`
		SortOrder   int    `json:"sort_order"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	cat.Name = req.Name
	cat.Description = req.Description
	cat.SortOrder = req.SortOrder
	h.DB.Save(&cat)
	c.JSON(http.StatusOK, cat)
}

func (h *CategoryHandler) Delete(c *gin.Context) {
	id, _ := parseInt(c.Param("id"), 0)
	h.DB.Delete(&models.ProductCategory{}, id)
	c.JSON(http.StatusOK, gin.H{"message": "已删除"})
}
