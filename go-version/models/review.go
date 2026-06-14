package models

import "time"

type Review struct {
	ID        uint      `gorm:"primaryKey" json:"id"`
	UserID    uint      `gorm:"index;not null" json:"user_id"`
	User      User      `gorm:"foreignKey:UserID" json:"user,omitempty"`
	ProductID uint      `gorm:"index;not null" json:"product_id"`
	OrderID   uint      `json:"order_id"`
	Rating    int       `gorm:"not null" json:"rating"`
	Content   string    `gorm:"type:text" json:"content"`
	CreatedAt time.Time `json:"created_at"`
}
