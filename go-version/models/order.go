package models

import "time"

type OrderStatus string

const (
	OrderPending   OrderStatus = "pending"
	OrderPaid      OrderStatus = "paid"
	OrderCompleted OrderStatus = "completed"
	OrderRefunded  OrderStatus = "refunded"
	OrderCancelled OrderStatus = "cancelled"
)

type Order struct {
	ID         uint        `gorm:"primaryKey" json:"id"`
	OrderNo    string      `gorm:"uniqueIndex;size:50;not null" json:"order_no"`
	UserID     uint        `gorm:"index;not null" json:"user_id"`
	TotalPrice float64     `gorm:"not null" json:"total_price"`
	Discount   float64     `gorm:"default:0" json:"discount"`
	FinalPrice float64     `gorm:"not null" json:"final_price"`
	CouponID   *uint       `json:"coupon_id,omitempty"`
	Status     OrderStatus `gorm:"size:20;default:pending" json:"status"`
	Items      []OrderItem `gorm:"foreignKey:OrderID" json:"items,omitempty"`
	CardKeys   []CardKey   `gorm:"foreignKey:OrderID" json:"card_keys,omitempty"`
	CreatedAt  time.Time   `json:"created_at"`
	UpdatedAt  time.Time   `json:"updated_at"`
}

type OrderItem struct {
	ID        uint    `gorm:"primaryKey" json:"id"`
	OrderID   uint    `gorm:"index;not null" json:"order_id"`
	ProductID uint    `gorm:"not null" json:"product_id"`
	Product   Product `gorm:"foreignKey:ProductID" json:"product,omitempty"`
	Price     float64 `gorm:"not null" json:"price"`
	Quantity  int     `gorm:"not null;default:1" json:"quantity"`
}
