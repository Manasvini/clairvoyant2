// Code generated by protoc-gen-go-grpc. DO NOT EDIT.

package contentserver

import (
	context "context"
	grpc "google.golang.org/grpc"
	codes "google.golang.org/grpc/codes"
	status "google.golang.org/grpc/status"
)

// This is a compile-time assertion to ensure that this generated file
// is compatible with the grpc package it is being compiled against.
// Requires gRPC-Go v1.32.0 or later.
const _ = grpc.SupportPackageIsVersion7

// ContentClient is the client API for Content service.
//
// For semantics around ctx use and closing/ending streaming RPCs, please refer to https://pkg.go.dev/google.golang.org/grpc/?tab=doc#ClientConn.NewStream.
type ContentClient interface {
	GetSegment(ctx context.Context, in *SegmentRequest, opts ...grpc.CallOption) (*SegmentResponse, error)
}

type contentClient struct {
	cc grpc.ClientConnInterface
}

func NewContentClient(cc grpc.ClientConnInterface) ContentClient {
	return &contentClient{cc}
}

func (c *contentClient) GetSegment(ctx context.Context, in *SegmentRequest, opts ...grpc.CallOption) (*SegmentResponse, error) {
	out := new(SegmentResponse)
	err := c.cc.Invoke(ctx, "/contentserver.Content/getSegment", in, out, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

// ContentServer is the server API for Content service.
// All implementations must embed UnimplementedContentServer
// for forward compatibility
type ContentServer interface {
	GetSegment(context.Context, *SegmentRequest) (*SegmentResponse, error)
	mustEmbedUnimplementedContentServer()
}

// UnimplementedContentServer must be embedded to have forward compatible implementations.
type UnimplementedContentServer struct {
}

func (UnimplementedContentServer) GetSegment(context.Context, *SegmentRequest) (*SegmentResponse, error) {
	return nil, status.Errorf(codes.Unimplemented, "method GetSegment not implemented")
}
func (UnimplementedContentServer) mustEmbedUnimplementedContentServer() {}

// UnsafeContentServer may be embedded to opt out of forward compatibility for this service.
// Use of this interface is not recommended, as added methods to ContentServer will
// result in compilation errors.
type UnsafeContentServer interface {
	mustEmbedUnimplementedContentServer()
}

func RegisterContentServer(s grpc.ServiceRegistrar, srv ContentServer) {
	s.RegisterService(&Content_ServiceDesc, srv)
}

func _Content_GetSegment_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(SegmentRequest)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(ContentServer).GetSegment(ctx, in)
	}
	info := &grpc.UnaryServerInfo{
		Server:     srv,
		FullMethod: "/contentserver.Content/getSegment",
	}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(ContentServer).GetSegment(ctx, req.(*SegmentRequest))
	}
	return interceptor(ctx, in, info, handler)
}

// Content_ServiceDesc is the grpc.ServiceDesc for Content service.
// It's only intended for direct use with grpc.RegisterService,
// and not to be introspected or modified (even as a copy)
var Content_ServiceDesc = grpc.ServiceDesc{
	ServiceName: "contentserver.Content",
	HandlerType: (*ContentServer)(nil),
	Methods: []grpc.MethodDesc{
		{
			MethodName: "getSegment",
			Handler:    _Content_GetSegment_Handler,
		},
	},
	Streams:  []grpc.StreamDesc{},
	Metadata: "contentserver.proto",
}