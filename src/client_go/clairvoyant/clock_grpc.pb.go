// Code generated by protoc-gen-go-grpc. DO NOT EDIT.

package clairvoyant

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

// ClockServerClient is the client API for ClockServer service.
//
// For semantics around ctx use and closing/ending streaming RPCs, please refer to https://pkg.go.dev/google.golang.org/grpc/?tab=doc#ClientConn.NewStream.
type ClockServerClient interface {
	HandleSyncRequest(ctx context.Context, in *SyncRequest, opts ...grpc.CallOption) (*SyncResponse, error)
}

type clockServerClient struct {
	cc grpc.ClientConnInterface
}

func NewClockServerClient(cc grpc.ClientConnInterface) ClockServerClient {
	return &clockServerClient{cc}
}

func (c *clockServerClient) HandleSyncRequest(ctx context.Context, in *SyncRequest, opts ...grpc.CallOption) (*SyncResponse, error) {
	out := new(SyncResponse)
	err := c.cc.Invoke(ctx, "/clairvoyant.ClockServer/HandleSyncRequest", in, out, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

// ClockServerServer is the server API for ClockServer service.
// All implementations must embed UnimplementedClockServerServer
// for forward compatibility
type ClockServerServer interface {
	HandleSyncRequest(context.Context, *SyncRequest) (*SyncResponse, error)
	mustEmbedUnimplementedClockServerServer()
}

// UnimplementedClockServerServer must be embedded to have forward compatible implementations.
type UnimplementedClockServerServer struct {
}

func (UnimplementedClockServerServer) HandleSyncRequest(context.Context, *SyncRequest) (*SyncResponse, error) {
	return nil, status.Errorf(codes.Unimplemented, "method HandleSyncRequest not implemented")
}
func (UnimplementedClockServerServer) mustEmbedUnimplementedClockServerServer() {}

// UnsafeClockServerServer may be embedded to opt out of forward compatibility for this service.
// Use of this interface is not recommended, as added methods to ClockServerServer will
// result in compilation errors.
type UnsafeClockServerServer interface {
	mustEmbedUnimplementedClockServerServer()
}

func RegisterClockServerServer(s grpc.ServiceRegistrar, srv ClockServerServer) {
	s.RegisterService(&ClockServer_ServiceDesc, srv)
}

func _ClockServer_HandleSyncRequest_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(SyncRequest)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(ClockServerServer).HandleSyncRequest(ctx, in)
	}
	info := &grpc.UnaryServerInfo{
		Server:     srv,
		FullMethod: "/clairvoyant.ClockServer/HandleSyncRequest",
	}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(ClockServerServer).HandleSyncRequest(ctx, req.(*SyncRequest))
	}
	return interceptor(ctx, in, info, handler)
}

// ClockServer_ServiceDesc is the grpc.ServiceDesc for ClockServer service.
// It's only intended for direct use with grpc.RegisterService,
// and not to be introspected or modified (even as a copy)
var ClockServer_ServiceDesc = grpc.ServiceDesc{
	ServiceName: "clairvoyant.ClockServer",
	HandlerType: (*ClockServerServer)(nil),
	Methods: []grpc.MethodDesc{
		{
			MethodName: "HandleSyncRequest",
			Handler:    _ClockServer_HandleSyncRequest_Handler,
		},
	},
	Streams:  []grpc.StreamDesc{},
	Metadata: "clock.proto",
}
